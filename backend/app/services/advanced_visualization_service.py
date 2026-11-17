"""Bounded, evidence-based static repository visualization extraction."""
from __future__ import annotations
import ast, json, logging, os, re, sys
from collections import Counter, defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)
EXCLUDED = {'.git','node_modules','venv','.venv','__pycache__','dist','build','.next','coverage','.pytest_cache','.mypy_cache'}
SECRET_NAMES = {'.env','.env.local','.env.production','id_rsa','id_ed25519'}
SECRET_SUFFIXES = {'.pem','.key','.p12','.pfx'}
EXT_LANG = {'.py':'Python','.pyi':'Python','.js':'JavaScript','.jsx':'JavaScript','.mjs':'JavaScript','.cjs':'JavaScript','.ts':'TypeScript','.tsx':'TypeScript','.java':'Java','.kt':'Kotlin','.go':'Go','.rs':'Rust','.rb':'Ruby','.php':'PHP','.cs':'C#','.cpp':'C++','.c':'C','.h':'C/C++','.hpp':'C++','.swift':'Swift','.scala':'Scala','.html':'HTML','.css':'CSS','.scss':'SCSS','.vue':'Vue','.svelte':'Svelte','.sh':'Shell','.sql':'SQL'}
MANIFESTS = {'package.json','requirements.txt','pyproject.toml','Pipfile','pom.xml','build.gradle','build.gradle.kts','Cargo.toml','go.mod','composer.json','Gemfile','Dockerfile'}
MAX_FILES=12000; MAX_DIRS=3000; MAX_DEPTH=12; MAX_FILE_BYTES=512_000; MAX_TOTAL_SOURCE_BYTES=32*1024*1024; MAX_GRAPH_NODES=300; MAX_GRAPH_EDGES=900

def _safe_file(p: Path) -> bool:
 n=p.name.lower()
 return n not in SECRET_NAMES and not n.startswith('.env') and p.suffix.lower() not in SECRET_SUFFIXES and not n.endswith(('.pem','.key'))

def analyze_repository(root_path: str) -> dict:
 root=Path(root_path).resolve()
 if not root.is_dir(): raise ValueError('Repository path is not a directory')
 files=[]; dirs=set(); warnings=[]; truncated=False
 for base, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
  bp=Path(base)
  try: depth=len(bp.relative_to(root).parts)
  except ValueError: dirnames[:]=[]; continue
  dirnames[:]=sorted(d for d in dirnames if d not in EXCLUDED and not (bp/d).is_symlink())
  if depth >= MAX_DEPTH:
   if dirnames: warnings.append(f'Directory depth limit ({MAX_DEPTH}) reached.'); truncated=True
   dirnames[:]=[]
  for d in dirnames:
   if len(dirs) >= MAX_DIRS:
    dirnames[:]=[]; truncated=True; warnings.append(f'Directory limit ({MAX_DIRS}) reached.'); break
   dirs.add((bp/d).relative_to(root).as_posix())
  for name in filenames:
   p=bp/name
   if p.is_symlink() or not _safe_file(p): continue
   try:
    st=p.stat()
    if not p.is_file(): continue
    rel=p.relative_to(root).as_posix()
    files.append({'path':rel,'name':name,'extension':p.suffix.lower() or '[no extension]','size':st.st_size})
   except OSError: continue
   if len(files)>=MAX_FILES:
    truncated=True; warnings.append(f'File limit ({MAX_FILES}) reached.'); break
  if len(files)>=MAX_FILES: break
 files.sort(key=lambda x:x['path'].lower())
 lang=Counter(EXT_LANG[f['extension']] for f in files if f['extension'] in EXT_LANG)
 ext=Counter(f['extension'] for f in files)
 def dist(c):
  total=sum(c.values()); return [{'name':k,'count':v,'percentage':round(v*100/total,2) if total else 0} for k,v in c.most_common()]
 tree={'name':root.name,'path':'.','type':'directory','children':[]}
 index={'.':tree}
 for d in sorted(dirs,key=lambda x:(x.count('/'),x.lower())):
  parent=d.rpartition('/')[0] or '.'; node={'name=d':None}
  node={'name':d.rsplit('/',1)[-1],'path':d,'type':'directory','children':[]}
  if parent in index: index[parent]['children'].append(node); index[d]=node
 for f in files:
  parent=f['path'].rpartition('/')[0] or '.'
  node={'name':f['name'],'path':f['path'],'type':'file','extension':f['extension'],'size':f['size']}
  if parent in index: index[parent]['children'].append(node)
 for n in index.values(): n.get('children',[]).sort(key=lambda x:(x['type']!='directory',x['name'].lower()))
 technologies=[]; tech_seen=set(); remaining_bytes=MAX_TOTAL_SOURCE_BYTES
 def addtech(name,kind,evidence):
  key=(name.lower(),kind)
  if key not in tech_seen: tech_seen.add(key); technologies.append({'name':name,'category':kind,'evidence':evidence})
 pydeps=set(); jsdeps=set(); package_evidence=[]
 for f in files:
  name=f['name']; rel=f['path']; p=root/rel
  if name not in MANIFESTS: continue
  try:
   size=p.stat().st_size
   if size>MAX_FILE_BYTES or size>remaining_bytes: continue
   txt=p.read_text('utf-8',errors='replace'); remaining_bytes-=size
  except OSError: continue
  package_evidence.append(rel)
  if name=='package.json':
   try:
    data=json.loads(txt)
    for section in ('dependencies','devDependencies','peerDependencies','optionalDependencies'):
     for dep in (data.get(section) or {}):
      jsdeps.add(dep)
      low=dep.lower(); category='Framework' if low in {'react','vue','angular','next','nuxt','svelte','express','fastify','nestjs'} else ('Build tooling' if low in {'vite','webpack','rollup','typescript','eslint','prettier'} else 'Library')
      addtech(dep,category,rel)
    if data.get('scripts'): addtech('npm scripts','Build tooling',rel)
   except Exception: warnings.append(f'Could not parse {rel}.')
  elif name in ('requirements.txt','Pipfile','pyproject.toml'):
   for line in txt.splitlines():
    m=re.match(r'^\s*([A-Za-z0-9_.-]+)\s*(?:[<=>~!;\[]|$)',line)
    if m and not line.lstrip().startswith(('#','[')): pydeps.add(m.group(1))
   for dep in sorted(pydeps): addtech(dep,'Python package',rel)
   if 'fastapi' in txt.lower(): addtech('FastAPI','Framework',rel)
   if 'django' in txt.lower(): addtech('Django','Framework',rel)
  elif name in ('pom.xml','build.gradle','build.gradle.kts','Cargo.toml','go.mod','composer.json','Gemfile'):
   addtech({'pom.xml':'Maven','build.gradle':'Gradle','build.gradle.kts':'Gradle','Cargo.toml':'Cargo','go.mod':'Go modules','composer.json':'Composer','Gemfile':'Bundler'}[name],'Build / package manager',rel)
  elif name=='Dockerfile': addtech('Docker','Infrastructure',rel)
 # Language-appropriate dependency extraction without executing code.
 module_files={f['path']:f for f in files if f['extension'] in {'.py','.pyi','.js','.jsx','.mjs','.cjs','.ts','.tsx'}}
 module_set=set(module_files); edges=[]; external=set(); external_refs=[]; source_text={}
 def add_edge(src,dst,kind,evidence,confidence='detected'):
  if len(edges)<MAX_GRAPH_EDGES: edges.append({'source':src,'target':dst,'type':kind,'evidence':evidence,'confidence':confidence})
 for rel,f in module_files.items():
  p=root/rel
  try:
   if f['size']>MAX_FILE_BYTES or f['size']>remaining_bytes: continue
   content=p.read_text('utf-8',errors='replace'); remaining_bytes-=f['size']
  except (OSError,UnicodeError): continue
  source_text[rel]=content
  if f['extension'] in ('.py','.pyi'):
   try:
    parsed=ast.parse(content)
    imports=[]
    for item in ast.walk(parsed):
     if isinstance(item,ast.Import): imports += [(a.name.split('.')[0],a.name) for a in item.names]
     elif isinstance(item,ast.ImportFrom) and item.module: imports.append((item.module.split('.')[0],item.module))
    for top, full in imports:
     target=None
     candidates=[x for x in module_set if x.endswith('/'+full.replace('.','/')+'.py') or x==full.replace('.','/')+'.py' or x.endswith('/'+full.replace('.','/')+'/__init__.py')]
     if candidates: target=sorted(candidates)[0]
     elif top in {Path(x).stem for x in module_set}: target=next((x for x in module_set if Path(x).stem==top),None)
     if target: add_edge(rel,target,'internal',f'Python import: {full}')
     elif full not in {'os','sys','re','json','typing','pathlib','asyncio','logging','datetime','collections','math','subprocess','unittest','ast'}: external.add(top); external_refs.append((rel, top, f'Python import: {full}'))
   except (SyntaxError,ValueError): warnings.append(f'Python AST parsing skipped malformed file: {rel}')
  else:
   for m in re.finditer(r'''(?:import\s+(?:[^'";]+?\s+from\s+)?|export\s+[^'";]+?\s+from\s+|require\s*\()\s*['"]([^'"]+)['"]''',content):
    spec=m.group(1)
    if spec.startswith('.'):
     base=(Path(rel).parent/spec).as_posix()
     options=[base,base+'.js',base+'.jsx',base+'.ts',base+'.tsx',base+'.mjs',base+'/index.js',base+'/index.ts']
     target=next((x for x in options if x in module_set),None)
     if target: add_edge(rel,target,'internal',f'Static import/export: {spec}')
    else:
     package=spec.split('/')[0]; external.add(package); external_refs.append((rel, package, f'Static package import: {spec}'))
 for source, dep, evidence in external_refs:
  if len(edges)>=MAX_GRAPH_EDGES: break
  add_edge(source,'external:'+dep,'external-package',evidence,'detected')
 if remaining_bytes <= 0: warnings.append(f'Source analysis byte budget ({MAX_TOTAL_SOURCE_BYTES} bytes) reached; some files were skipped.')

 architecture, workflow = _build_architecture_workflow(root, files, module_set, edges, source_text)
 graph_nodes=[{'id':p,'label':p,'path':p,'package':p.split('/')[0],'type':'module'} for p in sorted(module_set)[:MAX_GRAPH_NODES]]
 graph_nodes += [{'id':'external:'+d,'label':d,'path':None,'package':'External packages','type':'external'} for d in sorted(external)[:80]]
 allowed={n['id'] for n in graph_nodes}
 graph_edges=[e for e in edges if e['source'] in allowed and e['target'] in allowed]
 incoming=Counter(e['target'] for e in graph_edges); outgoing=Counter(e['source'] for e in graph_edges)
 for n in graph_nodes:
  n['incoming_count']=incoming[n['id']]; n['outgoing_count']=outgoing[n['id']]
 if len(module_set)>MAX_GRAPH_NODES: warnings.append(f'Dependency graph limited to {MAX_GRAPH_NODES} modules.')
 if len(edges)>=MAX_GRAPH_EDGES: warnings.append(f'Dependency edge limit ({MAX_GRAPH_EDGES}) reached.')
 # Weakly connected internal dependency clusters (graph-derived, not inferred).
 parent={n['id']:n['id'] for n in graph_nodes if n['type']=='module'}
 def find(node):
  while parent[node]!=node:
   parent[node]=parent[parent[node]]
   node=parent[node]
  return node
 for edge in graph_edges:
  if edge['type']=='internal' and edge['source'] in parent and edge['target'] in parent:
   left,right=find(edge['source']),find(edge['target'])
   if left!=right: parent[right]=left
 cluster_map=defaultdict(list)
 for node in parent: cluster_map[find(node)].append(node)
 clusters=sorted((sorted(members) for members in cluster_map.values()),key=len,reverse=True)
 metrics={'node_count':len(graph_nodes),'edge_count':len(graph_edges),
  'most_incoming':sorted(graph_nodes,key=lambda n:n['incoming_count'],reverse=True)[:8],
  'most_outgoing':sorted(graph_nodes,key=lambda n:n['outgoing_count'],reverse=True)[:8],
  'isolated_modules':[n['id'] for n in graph_nodes if n['type']=='module' and not n['incoming_count'] and not n['outgoing_count']][:30],
  'largest_internal_clusters':[{'size':len(members),'modules':members[:20]} for members in clusters[:8]],
  'external_reference_counts':dict(Counter(e['target'].split(':',1)[-1] for e in graph_edges if e['type']=='external-package'))}
 return {'summary':{'total_files':len(files),'total_source_files':sum(lang.values()),'total_directories':len(dirs),'counting_method':'Files are counted, not lines of code.','truncated':truncated},'tree':tree,'languages':dist(lang),'extensions':dist(ext),'technologies':technologies,'dependency_graph':{'nodes':graph_nodes,'edges':graph_edges,'metrics':metrics,'limitations':['Static imports only; dynamic/runtime resolution is not performed.']},'architecture':architecture,'workflow':workflow,'warnings':list(dict.fromkeys(warnings)),'analyzed_root':root.name}


def _build_architecture_workflow(root, files, module_set, edges, source_text):
 """Create architecture components from subsystems and real import/call evidence."""
 component_files=defaultdict(list); file_component={}; file_layer={}
 def classify(path, content):
  low=path.lower(); name=Path(path).name.lower(); txt=content.lower()
  if name in {'dockerfile','docker-compose.yml','docker-compose.yaml','vite.config.js','webpack.config.js'} or name.endswith(('.yml','.yaml','.toml','.ini')): return 'Infrastructure / Configuration'
  if re.search(r'@(app|router)\.(get|post|put|patch|delete|websocket)\s*\(',content) or 'fastapi()' in txt: return 'API / Interface'
  if any(x in low for x in ('/routes/','/routers/','/controllers/','/endpoints/','/api/')): return 'API / Interface'
  if any(x in low for x in ('/components/','/pages/','/views/','/screens/')) or Path(path).suffix in {'.jsx','.tsx','.vue','.svelte'}: return 'Presentation'
  if any(x in low for x in ('/services/','/service/','/usecases/','/use_cases/')): return 'Business Logic'
  if any(x in low for x in ('/models/','/schemas/','/entities/','/repositories/')): return 'Data / Domain'
  if re.search(r'\b(sqlalchemy|psycopg|pymongo|motor|sqlite3|asyncpg|redis)\b',txt): return 'Persistence'
  if re.search(r'\b(requests|httpx|aiohttp|boto3|openai|ollama|stripe|twilio)\b',txt): return 'External Integration'
  if name in {'main.py','app.py','server.py','index.js','index.ts','main.ts','main.tsx','cli.py'}: return 'Application Entry'
  return 'Core Modules'
 def comp_name(path, layer):
  parts=Path(path).parts
  ignored={'backend','frontend','client','server','src','app','lib','packages'}
  folder=next((part for part in parts[:-1] if part not in ignored),None)
  return f'{layer}: {folder or Path(path).stem}'
 for rel in sorted(module_set):
  content=source_text.get(rel,'')
  layer=classify(rel,content); name=comp_name(rel,layer)
  component_files[(layer,name)].append(rel)
  file_layer[rel]=layer
 for item in files:
  rel=item['path']
  if rel not in file_layer and item['name'] in MANIFESTS:
   layer=classify(rel,''); name=comp_name(rel,layer)
   component_files[(layer,name)].append(rel); file_layer[rel]=layer
 nodes=[]
 for (layer,name),paths in sorted(component_files.items()):
  cid=re.sub(r'[^a-z0-9]+','-',(layer+'-'+name).lower()).strip('-')
  for path in paths: file_component[path]=cid
  symbols=[]
  for path in paths:
   content=source_text.get(path,'')
   if Path(path).suffix in {'.py','.pyi'}:
    try:
     parsed=ast.parse(content)
     symbols.extend(n.name for n in ast.walk(parsed) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)))
    except (SyntaxError,ValueError):
     pass
   else:
    symbols.extend(re.findall(r'\b(?:function|class)\s+([A-Za-z_$][\w$]*)',content)[:30])
  symbols=list(dict.fromkeys(symbols))[:12]
  description=(f'{len(paths)} file(s); source declares {", ".join(symbols[:6])}.' if symbols else
               f'{len(paths)} repository file(s) grouped from subsystem path and source evidence.')
  nodes.append({'id':cid,'name':name.split(': ',1)[-1],'layer':layer,
   'description':description,'symbols':symbols,
   'files':sorted(paths)[:100],'file_count':len(paths),'evidence':sorted(paths)[:12],
   'confidence':'inferred'})
 nodes=nodes[:90]; valid={n['id'] for n in nodes}
 grouped={}
 for e in edges:
  a=file_component.get(e['source']); b=file_component.get(e['target'])
  if a and b and a!=b and a in valid and b in valid:
   key=(a,b)
   row=grouped.setdefault(key,{'source':a,'target':b,'type':'imports','confidence':'detected','evidence':[],'source_paths':[]})
   row['evidence'].append(e['evidence']); row['source_paths'].append(e['source'])
 arch_edges=[]
 for row in grouped.values():
  row['evidence']=sorted(set(row['evidence']))[:8]; row['source_paths']=sorted(set(row['source_paths']))[:8]
  arch_edges.append(row)
 layer_order=['Presentation','API / Interface','Application Entry','Business Logic','Data / Domain','Persistence','External Integration','Infrastructure / Configuration','Core Modules']
 layer_names=sorted({n['layer'] for n in nodes},key=lambda x:layer_order.index(x) if x in layer_order else 99)
 architecture={'layers':[{'id':x,'name':x,'components':[n['id'] for n in nodes if n['layer']==x]} for x in layer_names],
  'nodes':nodes,'edges':arch_edges,
  'method':'Components are grouped from repository subsystems. Solid edges are statically detected imports; layer labels are inferred.',
  'limitations':['Layer assignment is heuristic.','Only detected static imports produce component relationships; runtime calls are not observed.']}

 # Build repository-specific control-flow graphs from Python AST. Unlike the
 # previous linear call-chain heuristic, this preserves branches, loops,
 # exception paths, returns, and the source locations that justify each node.
 function_index=defaultdict(list); entries=[]
 for rel,content in source_text.items():
  if Path(rel).suffix not in {'.py','.pyi'}: continue
  try: tree=ast.parse(content,filename=rel)
  except (SyntaxError,ValueError): continue
  for fn in [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]:
   function_index[fn.name].append((rel,fn))
   decorator_text=' '.join(ast.unparse(d) if hasattr(ast,'unparse') else '' for d in fn.decorator_list)
   if re.search(r'\.(get|post|put|patch|delete|websocket|route)\s*\(',decorator_text):
    entries.append({'name':fn.name,'path':rel,'line':fn.lineno,'kind':'API route','route':decorator_text[:140],'node':fn})
   elif fn.name in {'main','run','cli','entrypoint','create_app','create_application','application'}:
    entries.append({'name':fn.name,'path':rel,'line':fn.lineno,'kind':'application entry','node':fn})
  # Only regard a __main__ guard as an entry when it actually invokes code.
  for stmt in tree.body:
   if isinstance(stmt,ast.If) and isinstance(stmt.test,ast.Compare) and isinstance(stmt.test.left,ast.Name) and stmt.test.left.id=='__name__':
    invoked=[]
    for call in ast.walk(stmt):
     if isinstance(call,ast.Call):
      nm=call.func.id if isinstance(call.func,ast.Name) else call.func.attr if isinstance(call.func,ast.Attribute) else None
      if nm: invoked.append(nm)
    if invoked:
     entries.append({'name':'script entry','path':rel,'line':stmt.lineno,'kind':'script entry','node':stmt,'calls':invoked})
 # Stable de-duplication and avoid treating a helper definition as an entry
 # merely because its name happens to match a common convention in many files.
 unique=[]; seen_entries=set()
 for item in entries:
  key=(item['path'],item['name'],item['line'])
  if key not in seen_entries: seen_entries.add(key); unique.append(item)
 workflows=[]
 for entry in unique[:40]:
  steps=[]; flow_edges=[]; visited_functions=set(); max_steps=70
  def add_step(label,kind,node,path,confidence='detected',evidence=None):
   if len(steps)>=max_steps: return None
   sid=f"node-{len(steps)+1}"
   steps.append({'id':sid,'label':str(label)[:100],'kind':kind,'path':path,
    'line':getattr(node,'lineno',entry['line']),'end_line':getattr(node,'end_lineno',getattr(node,'lineno',entry['line'])),
    'confidence':confidence,'evidence':evidence or f"{type(node).__name__} at {path}:{getattr(node,'lineno',entry['line'])}"})
   return sid
  def connect(sources,target,label=None,kind='sequence'):
   if target is None:return
   for source in sources:
    if source and source!=target: flow_edges.append({'source':source,'target':target,'label':label,'type':kind,'confidence':'detected'})
  def called_functions(node):
   names=[]
   for call in ast.walk(node):
    if isinstance(call,ast.Call):
     name=call.func.id if isinstance(call.func,ast.Name) else call.func.attr if isinstance(call.func,ast.Attribute) else None
     if name and len(function_index.get(name,[]))==1:
      target_path,target_fn=function_index[name][0]
      if (target_path,target_fn.lineno)!=(entry['path'],getattr(entry.get('node'),'lineno',-1)): names.append((name,target_path,target_fn))
   return list(dict.fromkeys((n,p,f.lineno) for n,p,f in names))
  def emit_block(body,incoming,path,depth=0):
   current=list(incoming)
   if depth>8 or len(steps)>=max_steps:return current
   for stmt in body:
    if len(steps)>=max_steps: break
    if isinstance(stmt,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Pass)):
     continue
    if isinstance(stmt,ast.If):
     cond=add_step('If: '+(ast.unparse(stmt.test) if hasattr(ast,'unparse') else 'condition'), 'decision',stmt,path,
       evidence='Branch condition extracted from source code')
     connect(current,cond); yes=add_step('True branch','branch',stmt,path); no=add_step('False branch','branch',stmt,path)
     connect([cond],yes,'True','branch'); connect([cond],no,'False','branch')
     yes_end=emit_block(stmt.body,[yes],path,depth+1) or [yes]
     no_end=emit_block(stmt.orelse,[no],path,depth+1) if stmt.orelse else [no]
     merge=add_step('Continue','merge',stmt,path,evidence='Control-flow branches rejoin')
     connect(yes_end,merge,''); connect(no_end,merge,'')
     current=[merge]
    elif isinstance(stmt,(ast.For,ast.AsyncFor,ast.While)):
     test=add_step(('While: ' if isinstance(stmt,ast.While) else 'For each: ')+ (ast.unparse(stmt.test if isinstance(stmt,ast.While) else stmt.target) if hasattr(ast,'unparse') else 'loop'), 'loop',stmt,path,evidence='Loop construct extracted from source code')
     connect(current,test); body_start=add_step('Loop body','branch',stmt,path)
     connect([test],body_start,'Repeat','branch')
     body_end=emit_block(stmt.body,[body_start],path,depth+1) or [body_start]
     connect(body_end,test,'Next iteration','loop-back')
     exit_node=add_step('Exit loop','merge',stmt,path); connect([test],exit_node,'Done','branch')
     current=[exit_node]
    elif isinstance(stmt,(ast.Try,)):
     start=add_step('Try operation','process',stmt,path,evidence='Exception-handling block')
     connect(current,start); normal=emit_block(stmt.body,[start],path,depth+1) or [start]
     paths=list(normal)
     for handler in stmt.handlers:
      label='Exception: '+(ast.unparse(handler.type) if handler.type and hasattr(ast,'unparse') else 'any')
      branch=add_step(label,'branch',handler,path); connect([start],branch,'Exception','branch')
      paths.extend(emit_block(handler.body,[branch],path,depth+1) or [branch])
     if stmt.finalbody: paths=emit_block(stmt.finalbody,paths,path,depth+1)
     current=paths
    elif isinstance(stmt,(ast.Return,ast.Raise)):
     if isinstance(stmt,ast.Return) and stmt.value:
      for name,target_path,target_line in called_functions(stmt)[:3]:
       call_node=add_step(f"Call {name}()",'call',stmt,path,evidence=f"Return expression calls local function declared at {target_path}:{target_line}")
       connect(current,call_node); current=[call_node] if call_node else current
     label=('Return '+(ast.unparse(stmt.value) if stmt.value and hasattr(ast,'unparse') else 'result')) if isinstance(stmt,ast.Return) else 'Raise exception'
     terminal=add_step(label,'end' if isinstance(stmt,ast.Return) else 'error',stmt,path)
     connect(current,terminal); current=[]
    else:
     calls=called_functions(stmt)
     meaningful=isinstance(stmt,(ast.Assign,ast.AnnAssign,ast.AugAssign,ast.Expr,ast.Delete,ast.With,ast.AsyncWith,ast.Assert,ast.Break,ast.Continue))
     if meaningful:
      if isinstance(stmt,ast.Expr) and isinstance(stmt.value,ast.Call):
       func=stmt.value.func; label=func.id if isinstance(func,ast.Name) else func.attr if isinstance(func,ast.Attribute) else 'Call'
      elif isinstance(stmt,(ast.With,ast.AsyncWith)): label='Open context / resource'
      elif isinstance(stmt,ast.Assert): label='Assert: '+(ast.unparse(stmt.test) if hasattr(ast,'unparse') else 'condition')
      elif isinstance(stmt,ast.Break): label='Break loop'
      elif isinstance(stmt,ast.Continue): label='Continue loop'
      else: label=type(stmt).__name__.replace('Assign','Set values').replace('AugAssign','Update value').replace('AnnAssign','Define value')
      step=add_step(label,'process',stmt,path,evidence=f"{type(stmt).__name__} statement at {path}:{stmt.lineno}")
      connect(current,step); current=[step] if step else current
      # A local function call is represented explicitly and linked to its
      # declaration; recursion and ambiguous names are intentionally bounded.
      for name,target_path,target_line in calls[:3]:
       target_fn=next((fn for p,fn in function_index[name] if p==target_path and fn.lineno==target_line),None)
       if not target_fn or (target_path,target_line) in visited_functions: continue
       call_node=add_step(f"Call {name}()",'call',stmt,path,evidence=f"Local call resolves to {target_path}:{target_line}")
       connect(current,call_node); current=[call_node] if call_node else current
       visited_functions.add((target_path,target_line))
       # Include the callee's own meaningful statements one level deep. This
       # makes the flow repository-specific without exploding recursive graphs.
       if depth<2:
        callee_end=emit_block(target_fn.body,current,target_path,depth+1)
        if callee_end: current=callee_end
   return current
  entry_node=add_step('Start · '+entry['name']+' ('+entry['kind']+')','start',entry['node'],entry['path'],evidence=f"Entry point: {entry['path']}:{entry['line']}")
  if isinstance(entry['node'],(ast.FunctionDef,ast.AsyncFunctionDef)):
   current=emit_block(entry['node'].body,[entry_node],entry['path'])
  else:
   current=emit_block(entry['node'].body,[entry_node],entry['path'])
  if current:
   end=add_step('Workflow complete','end',entry['node'],entry['path'],confidence='inferred',evidence='End of statically reconstructed control flow')
   connect(current,end)
  if not steps: continue
  for idx,step in enumerate(steps): step['order']=idx
  # Keep edge order stable and avoid duplicate links created by nested branches.
  dedup=[]; edge_seen=set()
  for edge in flow_edges:
   key=(edge['source'],edge['target'],edge.get('label'),edge['type'])
   if key not in edge_seen: edge_seen.add(key); dedup.append(edge)
  workflows.append({'id':f"workflow-{len(workflows)+1}",'name':entry.get('route',entry['name'])[:100],
   'entry_point':{'name':entry['name'],'path':entry['path'],'line':entry['line'],'kind':entry['kind']},
   'steps':steps,'edges':dedup,
   'classification':'Static control-flow reconstruction from source code; not observed runtime execution.'})
 workflow={'workflows':workflows,'label':'Repository-specific control-flow workflows',
  'limitations':['Workflow extraction currently supports Python AST entry points and control-flow constructs.','Calls are resolved only when a local function name is unambiguous; dynamic dispatch and dependency injection may differ at runtime.','Branches and loops are statically inferred from source; runtime execution and actual branch outcomes are not observed.','Large workflows are bounded to 70 nodes per entry point and 40 entry points.']}
 return architecture,workflow



class AdvancedVisualizationService:
    """Service facade consumed by the repository orchestrator."""

    def analyze(self, repository_path: str) -> dict:
        """Return repository architecture and statically reconstructed workflows."""
        return analyze_repository(repository_path)
