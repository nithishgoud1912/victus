"""M5 browser checks against deterministic backend-contract fixtures."""
import json
import subprocess
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.local/9bc-browser'
OUT.mkdir(parents=True, exist_ok=True)
node = ROOT / '.local/toolchains/node-v24.22.0-win-x64/node.exe'
server = subprocess.Popen([str(node), 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5174'], cwd=ROOT/'dashboard', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1000})
  page.set_default_timeout(10000)
  mutations=[]; cursors=[]; errors=[]; submitted=False; expired=False
  page.on('pageerror',lambda e:errors.append(str(e)))
  task={'task_id':'fixture-task','tool':'fs.create_note','status':'running','verified':False}
  def route(r):
   global submitted
   path=r.request.url.split('8765')[-1].split('?')[0]
   method=r.request.method
   if method=='OPTIONS':r.fulfill(status=204,headers={'Access-Control-Allow-Origin':'http://127.0.0.1:5174','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'*'});return
   headers={'Access-Control-Allow-Origin':'http://127.0.0.1:5174'}
   body={}
   if method=='POST':mutations.append(path)
   if path=='/api/integrations':body={'cloud':'disabled','cloud_pin':None,'upstream':None,'mcp_notes':False}
   elif path=='/api/memory':body=[]
   elif path=='/api/voice':body={'enabled':False,'state':'idle','revision':0}
   elif path=='/api/session':body={'authenticated':True,'expires_at':None}
   elif path=='/api/health':body={'status':'ok','mode':'fixture','stopped':False,'tools':['fs.create_note'],'emergency_hotkey':'disabled'}
   elif path=='/api/tasks' and method=='POST': submitted=True;body={'task_id':'fixture-task','status':'queued'}
   elif path=='/api/tasks/fixture-task':body=task
   elif path=='/api/events':
    cursors.append(r.request.url)
    events=[]
    if submitted:
     for eid,kind,payload in [(1,'task.started',{}),(1,'task.started',{}),(2,'approval.required',{'approval_id':'fixture-approval'}),(2,'task.snapshot',task)]:
      data={'event_id':eid,'task_id':'fixture-task','event_type':kind,'timestamp':'fixture-time','safe_payload':payload}
      events.append(f'id: {eid}\nevent: {kind}\ndata: {json.dumps(data)}\n\n')
    r.fulfill(status=200,headers=headers,content_type='text/event-stream',body=''.join(events) or ': ping\n\n');return
   elif path=='/api/approvals/fixture-approval':body={'approval_id':'fixture-approval','task_id':'fixture-task','action_id':'act','tool_name':'fs.create_note','tool_version':'1','canonical_args_hash':'hash','policy_version':'1','target_identity':'note.txt','observation_identity':'obs','preview_ref':'p','expires_at':time.time()+(-1 if expired else 300),'state':'pending','created_at':time.time(),'updated_at':time.time()}
   elif path.endswith('/preview'):body={'filename':'note.txt','text':'<img src=x onerror=alert(1)> exact preview'}
   elif path=='/api/stop':body={'stopped':True,'reset':'restart'}
   elif path.endswith('/resolve'):body={'state':'denied'}
   else:raise AssertionError(path)
   r.fulfill(status=200,headers=headers,content_type='application/json',body=json.dumps(body))
  page.route('http://127.0.0.1:8765/**',route)
  for _ in range(80):
   try:page.goto('http://127.0.0.1:5174/');break
   except Exception:time.sleep(.1)
  page.screenshot(path=str(OUT/'initial.png'),full_page=True)
  page.get_by_label('Filename',exact=True).fill('note.txt')
  page.get_by_label('Command text / note content').fill('fixture note')
  page.get_by_role('button',name='Create note',exact=True).evaluate('(b)=>{b.click();b.click()}')
  expect(page.get_by_role('region',name='Action approval')).to_be_visible()
  assert mutations.count('/api/tasks')==1
  assert page.locator('li').filter(has_text='task.started').count()==1
  expect(page.get_by_label('Exact action preview')).to_contain_text('<img src=x')
  assert page.get_by_label('Exact action preview').locator('img').count()==0
  page.screenshot(path=str(OUT/'laptop.png'),full_page=True)
  for _ in range(40):
   if any('cursor=2' in url for url in cursors):break
   page.wait_for_timeout(100)
  assert any('cursor=2' in url for url in cursors)
  page.reload()
  expect(page.get_by_role('region',name='Action approval')).to_be_visible()
  assert mutations==['/api/tasks']
  expect(page.get_by_role('button',name='Create note',exact=True)).to_be_disabled()
  page.get_by_role('button',name='Deny',exact=True).focus();page.keyboard.press('Enter')
  assert mutations.count('/api/approvals/fixture-approval/resolve')==1
  page.reload()
  expect(page.get_by_role('button',name='Approve once')).to_be_enabled()
  page.get_by_role('button',name='Approve once').evaluate('(b)=>{b.click();b.click()}')
  expect(page.get_by_role('button',name='Approve once')).to_be_disabled()
  assert mutations.count('/api/approvals/fixture-approval/resolve')==2
  expired=True
  page.reload()
  expect(page.get_by_role('region',name='Action approval')).to_contain_text('Expired')
  expect(page.get_by_role('button',name='Approve once')).to_be_disabled()
  page.get_by_role('button',name='Stop all work').focus();page.keyboard.press('Enter')
  expect(page.get_by_role('button',name='Stop all work')).to_be_enabled()
  assert mutations.count('/api/stop')==1
  page.set_viewport_size({'width':390,'height':844})
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  box=page.get_by_role('button',name='Stop all work').bounding_box()
  assert box and box['y']>=0 and box['y']+box['height']<=844
  page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
  assert any('cursor=2' in url for url in cursors)
  assert not errors,errors
  (OUT/'report.json').write_text(json.dumps({'fixture_browser_checks':'passed','duplicate_submission':True,'event_replay':True,'reload_no_mutation':True,'expired_approval':True,'keyboard_deny_and_stop':True,'mobile_no_overflow':True,'page_errors':errors},indent=2))
  browser.close()
 print('M5 fixture browser checks passed')
finally:
 server.terminate();server.wait(timeout=10)

