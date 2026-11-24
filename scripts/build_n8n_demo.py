"""Build a credential-free n8n workflow from a public SYNTHETIC fixture."""
from pathlib import Path
import hashlib
import json
import textwrap

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'examples/demo_input.json').read_text())
STAGES = [
('01 | Load Synthetic SEO + CRM Data', 'const d = ' + json.dumps(DATA, separators=(',', ':')) + ';\nreturn [{json:d}];'),
('02 | Validate Source Dates + Metric Contracts', r'''
const d=$input.first().json;function check(x,msg){if(!x)throw new Error('QA blocked: '+msg)}
check(d.dataset_kind==='synthetic','production data cannot be used in public demo');
const g=d.gsc.daily,a=d.ga4.daily;
check(d.gsc.truncated===false&&d.ga4.truncated===false,'API row limit reached');
check(g.length>=14&&a.length>=14,'too few days');
const days=[...new Set(g.map(x=>x.date))].sort();
check(days.length===14,'GSC dates missing or duplicated');
check(g.every(x=>x.status==='final'&&Number.isInteger(x.clicks)&&x.clicks>=0&&x.clicks<=x.impressions),'GSC must be finalized');
check(a.every(x=>x.status==='matured'&&x.event_name==='prospectus_form_submit'&&Number.isInteger(x.event_count)),'GA4 event not confirmed/matured');
check(new Set(a.map(x=>x.date)).size===14,'GA4 date coverage missing');
check(d.clarity_snapshots.length<1000,'Clarity has hit API row cap');
check(d.crm_fixture.mode==='synthetic_fixture','CRM integration requires a connected account');
return [{json:{...d,qa:{coverage:'PASS',leadEvent:'prospectus_form_submit',sourceRows:g.length+a.length}}}];
'''),
('03 | Normalize + Deduplicate Upserts', r'''
const d=$input.first().json;
const dedupe=(rows,fields)=>{const by=new Map();for(const r of rows){const k=fields.map(f=>r[f]).join('|');if(by.has(k)&&JSON.stringify(by.get(k))!==JSON.stringify(r))throw new Error('Conflicting duplicate: '+k);by.set(k,r)}return [...by.values()]};
const g=dedupe(d.gsc.daily,['date']);const a=dedupe(d.ga4.daily,['date','event_name']);
const c=dedupe(d.crm_fixture.contacts,['contact_id']);
return [{json:{...d,gsc:{...d.gsc,daily:g},ga4:{...d.ga4,daily:a},crm_fixture:{...d.crm_fixture,contacts:c},qa:{...d.qa,deduped:true}}}];
'''),
('04 | Calculate Search + Prospectus Trends', r'''
const d=$input.first().json;const start=d.reporting_window.current_start;const sum=(rows,field,latest)=>rows.filter(x=>latest?x.date>=start:x.date<start).reduce((n,x)=>n+Number(x[field]||0),0);
const kpi=(rows,field)=>{const p=sum(rows,field,false),c=sum(rows,field,true);return {previous:p,current:c,change_pct:p?Math.round((c-p)*1000/p)/10:null}};
const stats={gsc_organic_clicks:kpi(d.gsc.daily,'clicks'),gsc_impressions:kpi(d.gsc.daily,'impressions'),ga4_organic_sessions:kpi(d.ga4.daily,'organic_sessions'),ga4_prospectus_form_submit_events:kpi(d.ga4.daily,'event_count')};
return [{json:{...d,stats}}];
'''),
('05 | CRM Adapter (Simulated) + Reconciliation', r'''
const d=$input.first().json,contacts=d.crm_fixture.contacts;const unique=new Set(contacts.map(x=>x.contact_id));if(unique.size!==contacts.length)throw new Error('CRM duplicate contact IDs');
const events=d.stats.ga4_prospectus_form_submit_events.current;
const crm={mode:'SYNTHETIC ONLY: no live CRM connection',unique_contacts:unique.size,ga4_event_occurrences:events,difference:events-unique.size,status:'needs_follow_up',note:'Event occurrences and unique CRM contacts have different measurement units.'};
return [{json:{...d,crm}}];
'''),
('06 | Clarity Organic / Paid Mobile Friction', r'''
const d=$input.first().json,rows=d.clarity_snapshots;const dates=[...new Set(rows.map(x=>x.captured_on))].sort();if(dates.length<2)throw new Error('Need two Clarity captures');const latest=dates.at(-1),before=dates.at(-2);const index=new Map(rows.filter(x=>x.captured_on===before).map(x=>[x.channel+'|'+x.device,x]));let issues=[];
for(const curr of rows.filter(x=>x.captured_on===latest)){
 if(!curr.verified||curr.dead_click_session_pct<0||curr.dead_click_session_pct>100)throw new Error('Invalid Clarity percentage');
 const key=curr.channel+'|'+curr.device,prev=index.get(key);if(!prev||Math.min(curr.sessions,prev.sessions)<100)continue;
 const diff=Math.round((curr.dead_click_session_pct-prev.dead_click_session_pct)*10)/10;
 if(curr.dead_click_session_pct>=15&&diff>=5)issues.push({segment:key,metric:'dead_click_session_pct',current_pct:curr.dead_click_session_pct,change_pp:diff,sessions:curr.sessions,action:'Inspect recordings and heatmaps, test CTA and forms'});
 if(curr.script_error_count>=10)issues.push({segment:key,metric:'script_error_count',events:curr.script_error_count,action:'Check JavaScript and form submission logs'});
}
return [{json:{...d,clarity_summary:{latest_capture:latest,scope:'sitewide channel x device',issues}}}];
'''),
('07 | Track Blog 7 / 14 / 28-Day Cohorts', r'''
const d=$input.first().json,utc=x=>new Date(x+'T00:00:00Z').getTime(),day=86400000,asof=utc(d.reporting_window.as_of);
const posts=d.posts.map(p=>{const pub=utc(p.publish_date),metrics={};for(const n of [7,14,28]){const last=pub+(n-1)*day,mature=asof>=pub+(n+1)*day;const rows=d.page_gsc_daily.filter(r=>r.post_id===p.post_id&&utc(r.date)>=pub&&utc(r.date)<=last);metrics[n]=!mature?{status:'awaiting_maturity'}:new Set(rows.map(r=>r.date)).size!==n?{status:'missing_historical_coverage',days_available:rows.length}:{status:'complete',clicks:rows.reduce((s,r)=>s+r.clicks,0)};}return {post_id:p.post_id,path:p.path,cohorts:metrics}});
return [{json:{...d,posts_summary:posts}}];
'''),
('08 | Simulate Idempotent Sheets Upserts + Readback', r'''
const d=$input.first().json,period=d.reporting_window.current_end,rows=[{row_key:period+'|organic_clicks',value:d.stats.gsc_organic_clicks.current},{row_key:period+'|prospectus_events',value:d.stats.ga4_prospectus_form_submit_events.current}];
const stored=new Map();for(const row of rows){stored.set(row.row_key,{...row});stored.set(row.row_key,{...row})}for(const row of rows){if(JSON.stringify(stored.get(row.row_key))!==JSON.stringify(row))throw new Error('Saved row differs from source');}
if(stored.size!==rows.length)throw new Error('Duplicate writes not suppressed');
return [{json:{...d,storage:{mode:'in-memory Sheets upsert simulation',readback_verified:true,unique_rows:stored.size,duplicate_write_attempts:rows.length}}}];
'''),
('09 | Publish Decision-Ready Demo Output', r'''
const d=$input.first().json,stats=d.stats;const alerts=[];
if(stats.gsc_organic_clicks.change_pct<=-20)alerts.push({metric:'organic_clicks',severity:'review',action:'Check rankings, top pages, search demand and crawl/index coverage'});
if(stats.ga4_prospectus_form_submit_events.change_pct<=-20)alerts.push({metric:'prospectus_form_submit_events',severity:'review',action:'Audit GA4 event firing and prospectus form path; do not claim this equals unique leads'});
for(const x of d.clarity_summary.issues)alerts.push({metric:x.metric,segment:x.segment,severity:'investigate',action:x.action});
const output={status:'DEMO_COMPLETE',data_kind:'SYNTHETIC - not client measurements',ga4_event_is_not_crm_lead:true,source_qa:d.qa,weekly_kpis:stats,crm_reconciliation:d.crm,clarity:d.clarity_summary,blog_cohorts:d.posts_summary,sheets_readback:d.storage,alerts,recommended_next_steps:alerts.slice(0,3).map(x=>x.action),business_efficiency_example:{before_hours_per_week:5,review_hours_per_week:1,estimated_hours_freed:4,disclaimer:'Illustrative assumptions, not measured time savings'}};
return [{json:output}];
''')]

nodes=[];connections={}
trigger='START | Run Synthetic End-to-End Demo'
nodes.append({'id':hashlib.md5(trigger.encode()).hexdigest(),'name':trigger,'type':'n8n-nodes-base.manualTrigger','typeVersion':1,'position':[240,320],'parameters':{}})
for i,(name,code) in enumerate(STAGES):
    nodes.append({'id':hashlib.md5(name.encode()).hexdigest(),'name':name,'type':'n8n-nodes-base.code','typeVersion':2,'position':[520+280*i,320],'parameters':{'mode':'runOnceForAllItems','jsCode':textwrap.dedent(code).strip()}})
allnames=[trigger]+[s[0] for s in STAGES]
for left,right in zip(allnames,allnames[1:]):
    connections[left]={'main':[[{'node':right,'type':'main','index':0}]]}
wf={'name':'PORTFOLIO DEMO | SEO Ops: Source → QA → CRM → UX → Report','nodes':nodes,'connections':connections,'settings':{'executionOrder':'v1','timezone':'Etc/UTC'},'active':False,'pinData':{},'meta':{'templateCredsSetupCompleted':True}}
path=ROOT/'workflows'/'n8n-import-demo.json'
path.write_text(json.dumps(wf,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(f'Generated {path.relative_to(ROOT)} ({len(nodes)} credential-free nodes)')
