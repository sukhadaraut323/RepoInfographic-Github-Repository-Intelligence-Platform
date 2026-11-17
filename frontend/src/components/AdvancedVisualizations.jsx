import { useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const COLORS = ['#8b91ff', '#3fd5e8', '#a78bfa', '#5eead4', '#fbbf24', '#fb7185', '#94a3b8']
const TOOLTIP = { contentStyle: { backgroundColor: '#101827', border: '1px solid #64748b', borderRadius: 9, color: '#f8fafc', padding: '10px 12px', boxShadow: '0 8px 24px rgba(0,0,0,.45)' }, labelStyle: { color: '#ffffff', fontWeight: 700 }, itemStyle: { color: '#e2e8f0' }, cursor: { fill: 'rgba(139,145,255,0.10)' } }
const fmt = (n) => Number(n || 0).toLocaleString()
function Panel({ title, children, note }) { return <section className="min-w-0 rounded-2xl border border-line bg-surface p-5"><h3 className="mb-4 font-display text-lg font-bold">{title}</h3>{children}{note && <p className="mt-3 text-xs text-muted">{note}</p>}</section> }
function Empty({ children = 'No evidence was available for this visualization.' }) { return <p className="py-7 text-sm text-muted">{children}</p> }
function TreeNode({ node, depth = 0 }) {
 const [open, setOpen] = useState(depth < 1)
 const folder = node.type === 'directory'
 return <div style={{ paddingLeft: depth * 14 }}><button type="button" onClick={() => folder && setOpen(v => !v)} className="flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm text-text hover:bg-raised" aria-expanded={folder ? open : undefined}><span className="w-4 text-muted">{folder ? (open ? '▾' : '▸') : '·'}</span><span>{folder ? '📁' : '📄'}</span><span className="min-w-0 truncate">{node.name}</span>{!folder && <span className="ml-auto shrink-0 text-xs text-muted">{node.extension} · {fmt(node.size)} B</span>}</button>{folder && open && (node.children || []).map(child => <TreeNode key={child.path} node={child} depth={depth + 1} />)}</div>
}
function GraphControls({ scale, setScale, reset, fit }) {
 return <div className="flex flex-wrap items-center gap-2"><button className="control" onClick={() => setScale(v => Math.min(2.2, v + .15))}>＋ Zoom</button><button className="control" onClick={() => setScale(v => Math.max(.45, v - .15))}>－ Zoom</button><button className="control" onClick={fit}>Fit</button><button className="control" onClick={reset}>Reset</button><span className="text-xs text-muted">{Math.round(scale * 100)}%</span></div>
}
function Architecture({ architecture }) {
 const nodes = architecture?.nodes || [], edges = architecture?.edges || []
 const [selected, setSelected] = useState(null), [scale, setScale] = useState(1), [offset, setOffset] = useState({x:0,y:0})
 const positioned = useMemo(() => {
  const layers = architecture?.layers?.length ? architecture.layers.map(l=>l.name) : [...new Set(nodes.map(n=>n.layer))]
  const col = new Map(layers.map((l,i)=>[l,i]))
  const counts = {}
  return nodes.map(n => { const c=col.get(n.layer)||0, r=counts[c]||0; counts[c]=r+1; return {...n,x:35+c*300,y:35+r*145} })
 }, [nodes, architecture?.layers])
 const pos = Object.fromEntries(positioned.map(n=>[n.id,n]))
 const width = Math.max(850, (Math.max(1,...positioned.map(n=>n.x/300+1)))*300)
 const height = Math.max(260, ...positioned.map(n=>n.y+125))
 const selectedNode = positioned.find(n=>n.id===selected)
 const relatedEdges = selected ? edges.filter(e=>e.source===selected||e.target===selected) : edges
 const download = () => {
  const svg=document.getElementById('architecture-svg'); if(!svg)return
  const clone=svg.cloneNode(true); clone.setAttribute('xmlns','http://www.w3.org/2000/svg')
  const xml=new XMLSerializer().serializeToString(clone); const url=URL.createObjectURL(new Blob([xml],{type:'image/svg+xml;charset=utf-8'}))
  const img=new Image()
  img.onload=()=>{const canvas=document.createElement('canvas');canvas.width= Math.max(1200,width*2);canvas.height=Math.max(700,height*2);const ctx=canvas.getContext('2d');ctx.fillStyle='#101827';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);URL.revokeObjectURL(url);canvas.toBlob(blob=>{if(!blob)return;const a=document.createElement('a');const u=URL.createObjectURL(blob);a.href=u;a.download='repository-architecture.png';a.click();URL.revokeObjectURL(u)},'image/png')}
  img.onerror=()=>URL.revokeObjectURL(url);img.src=url
 }
 if(!nodes.length)return <Empty>Static analysis could not identify meaningful architectural components for this repository.</Empty>
 return <div>
  <div className="mb-3 flex flex-wrap justify-between gap-3"><GraphControls scale={scale} setScale={setScale} reset={()=>{setScale(1);setOffset({x:0,y:0})}} fit={()=>{setScale(Math.min(1,900/width));setOffset({x:0,y:0})}}/><button onClick={download} className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:opacity-90">Download Architecture PNG</button></div>
  <div className="mb-3 flex flex-wrap gap-3 text-xs text-muted"><span><i className="mr-1 inline-block h-2 w-5 bg-accent"/>Detected import relationship (solid)</span><span><i className="mr-1 inline-block h-2 w-5 border-t-2 border-dashed border-primary"/>Inferred sequence / grouping</span><span>Click a component to inspect it; drag the canvas to pan.</span></div>
  <div className="max-h-[650px] overflow-auto rounded-xl border border-line bg-[#0d1422]">
   <svg id="architecture-svg" viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="img" aria-label="Evidence-based layered repository architecture" onWheel={e=>{e.preventDefault();setScale(v=>Math.max(.45,Math.min(2.2,v+(e.deltaY<0?.08:-.08))))}} onPointerDown={e=>{if(e.target===e.currentTarget){e.currentTarget.setPointerCapture(e.pointerId);e.currentTarget.dataset.drag=`${e.clientX-offset.x},${e.clientY-offset.y}`}}} onPointerMove={e=>{if(e.currentTarget.dataset.drag){const [x,y]=e.currentTarget.dataset.drag.split(',').map(Number);setOffset({x:e.clientX-x,y:e.clientY-y})}}} onPointerUp={e=>{delete e.currentTarget.dataset.drag}}>
    <defs><marker id="arch-arrow-new" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0 0 L0 6 L8 3z" fill="#3fd5e8"/></marker></defs>
    <g transform={`translate(${offset.x} ${offset.y}) scale(${scale})`}>
     {(architecture.layers||[]).map((l,i)=><g key={l.id}><text x={35+i*300} y="19" fill="#cbd5e1" fontSize="13" fontWeight="700">{l.name}</text><line x1={35+i*300} y1="25" x2={35+i*300+255} y2="25" stroke="#334155"/></g>)}
     {relatedEdges.map((e,i)=>{const a=pos[e.source],b=pos[e.target];if(!a||!b)return null;return <g key={i} opacity={selected && e.source!==selected && e.target!==selected ? 0.45 : 1}><path d={`M ${a.x+245} ${a.y+52} C ${a.x+280} ${a.y+52}, ${b.x-30} ${b.y+52}, ${b.x} ${b.y+52}`} stroke="#3fd5e8" strokeWidth="2" fill="none" markerEnd="url(#arch-arrow-new)"/><title>{`${e.type}: ${(e.evidence||[]).join('; ')}`}</title></g>})}
     {positioned.map(n=><g key={n.id} onClick={()=>setSelected(n.id)} style={{cursor:'pointer'}}><rect x={n.x} y={n.y} width="245" height="105" rx="10" fill={selected===n.id?'#263b59':'#18263b'} stroke={selected===n.id?'#fbbf24':'#64748b'} strokeWidth={selected===n.id?3:1.5}/><text x={n.x+12} y={n.y+23} fill="#f8fafc" fontSize="14" fontWeight="700">{n.name.slice(0,27)}</text><text x={n.x+12} y={n.y+45} fill="#cbd5e1" fontSize="11">{n.layer}</text><text x={n.x+12} y={n.y+65} fill="#a5b4fc" fontSize="11">{n.file_count} files · inferred grouping</text><text x={n.x+12} y={n.y+84} fill="#cbd5e1" fontSize="10">{(n.files||[])[0]||''}</text></g>)}
    </g>
   </svg>
  </div>
  {selectedNode && <div className="mt-3 rounded-xl border border-line bg-raised p-4"><div className="flex justify-between gap-3"><h4 className="font-semibold text-text">{selectedNode.name}</h4><button className="text-sm text-accent" onClick={()=>setSelected(null)}>Clear</button></div><p className="mt-1 text-sm text-muted">{selectedNode.layer} · {selectedNode.file_count} associated files</p><p className="mt-2 text-sm text-text">{selectedNode.description}</p><p className="mt-3 text-xs font-semibold text-muted">Source files</p><ul className="mt-1 max-h-36 list-disc overflow-auto pl-5 text-xs text-text">{(selectedNode.files||[]).map(f=><li key={f}>{f}</li>)}</ul><p className="mt-2 text-xs text-muted">Incoming: {edges.filter(e=>e.target===selected).length} · Outgoing: {edges.filter(e=>e.source===selected).length}</p>{edges.filter(e=>e.source===selected||e.target===selected).map((e,i)=><p key={i} className="mt-1 text-xs text-muted">{e.source} → {e.target} · {e.type} · {e.confidence} · {(e.evidence||[]).join(', ')}</p>)}</div>}
 </div>
}
function DependencyGraph({ graph }) {
 const [filter,setFilter]=useState('all'),[query,setQuery]=useState(''),[selected,setSelected]=useState(null),[selectedEdge,setSelectedEdge]=useState(null),[scale,setScale]=useState(1),[offset,setOffset]=useState({x:0,y:0})
 const nodes=graph?.nodes||[],edges=graph?.edges||[]
 const filteredNodes=useMemo(()=>nodes.filter(n=>(filter==='all'||(filter==='internal'?n.type==='module':n.type==='external'))&&(!query||n.label.toLowerCase().includes(query.toLowerCase())||String(n.path||'').toLowerCase().includes(query.toLowerCase()))).slice(0,180),[nodes,filter,query])
 const ids=new Set(filteredNodes.map(n=>n.id))
 const filteredEdges=edges.filter(e=>ids.has(e.source)&&ids.has(e.target)&&(filter==='all'||(filter==='internal'?e.type==='internal':e.type==='external-package')))
 const layout=useMemo(()=>{const groups={};const packages=[...new Set(filteredNodes.map(n=>n.package||'Other'))].sort();const columns=Object.fromEntries(packages.map((name,index)=>[name,index]));return filteredNodes.map(n=>{const group=n.package||'Other';const col=columns[group]||0;const row=groups[group]||0;groups[group]=row+1;return {...n,x:40+col*260,y:45+row*105}})},[filteredNodes])
 const pos=Object.fromEntries(layout.map(n=>[n.id,n]))
 const selectedNode=layout.find(n=>n.id===selected)
 const incoming=selected?filteredEdges.filter(e=>e.target===selected):[],outgoing=selected?filteredEdges.filter(e=>e.source===selected):[]
 const relevant=new Set([selected,...incoming.map(e=>e.source),...outgoing.map(e=>e.target)].filter(Boolean))
 const metrics=graph?.metrics||{}
 if(!nodes.length)return <Empty>No static dependency relationships were detected in the analyzed source files.</Empty>
 return <div>
  <div className="mb-3 flex flex-wrap items-center gap-2"><select value={filter} onChange={e=>{setFilter(e.target.value);setSelected(null)}} className="rounded-lg border border-line bg-raised px-3 py-2 text-sm text-text"><option value="all">All dependencies</option><option value="internal">Internal modules</option><option value="external">External packages</option></select><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search module or package…" className="min-w-0 flex-1 rounded-lg border border-line bg-raised px-3 py-2 text-sm text-text placeholder:text-muted"/><span className="text-xs text-muted">{filteredNodes.length} nodes · {filteredEdges.length} edges</span></div>
  <div className="mb-3"><GraphControls scale={scale} setScale={setScale} reset={()=>{setScale(1);setOffset({x:0,y:0});setSelected(null);setSelectedEdge(null)}} fit={()=>{setScale(.75);setOffset({x:0,y:0})}}/></div>
  <div className="max-h-[620px] overflow-auto rounded-xl border border-line bg-[#0d1422]">
   <svg viewBox={`0 0 ${Math.max(850,...layout.map(n=>n.x+235))} ${Math.max(300,...layout.map(n=>n.y+90))}`} width={Math.max(850,...layout.map(n=>n.x+235))} height={Math.max(300,...layout.map(n=>n.y+90))} onWheel={e=>{e.preventDefault();setScale(v=>Math.max(.4,Math.min(2.3,v+(e.deltaY<0?.08:-.08))))}} onPointerDown={e=>{if(e.target===e.currentTarget){e.currentTarget.setPointerCapture(e.pointerId);e.currentTarget.dataset.drag=`${e.clientX-offset.x},${e.clientY-offset.y}`}}} onPointerMove={e=>{if(e.currentTarget.dataset.drag){const [x,y]=e.currentTarget.dataset.drag.split(',').map(Number);setOffset({x:e.clientX-x,y:e.clientY-y})}}} onPointerUp={e=>{delete e.currentTarget.dataset.drag}} role="img" aria-label="Interactive directed module dependency graph">
    <defs><marker id="dep-arrow-new" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0 0 L0 6 L8 3z" fill="#8b91ff"/></marker></defs>
    <g transform={`translate(${offset.x} ${offset.y}) scale(${scale})`}>
     {filteredEdges.map((e,i)=>{const a=pos[e.source],b=pos[e.target];if(!a||!b)return null;const active=!selected||relevant.has(e.source)&&relevant.has(e.target);return <path key={i} d={`M${a.x+205} ${a.y+32} L${b.x} ${b.y+32}`} stroke={e.type==='external-package'?'#fbbf24':'#8b91ff'} strokeWidth={selected&&(e.source===selected||e.target===selected)?3:1.4} opacity={active?0.75:0.08} fill="none" markerEnd="url(#dep-arrow-new)" onClick={()=>setSelectedEdge(e)} style={{cursor:'pointer'}}><title>{`${e.source} depends on ${e.target}: ${e.evidence}`}</title></path>})}
     {layout.map(n=>{const active=!selected||relevant.has(n.id);return <g key={n.id} onClick={()=>{setSelected(n.id);setSelectedEdge(null)}} style={{cursor:'pointer'}} opacity={active?1:.18}><rect x={n.x} y={n.y} width="205" height="66" rx="9" fill={n.type==='external'?'#3b2e19':'#1b2941'} stroke={selected===n.id?'#fbbf24':n.type==='external'?'#f59e0b':'#64748b'} strokeWidth={selected===n.id?3:1.4}/><text x={n.x+10} y={n.y+24} fill="#f8fafc" fontSize="12" fontWeight="700">{n.label.slice(0,27)}</text><text x={n.x+10} y={n.y+45} fill="#cbd5e1" fontSize="10">{n.type==='external'?'External package':`${n.incoming_count} in · ${n.outgoing_count} out`}</text></g>})}
    </g>
   </svg>
  </div>
  <div className="mt-3 grid gap-3 md:grid-cols-2"><div className="rounded-xl bg-raised p-3 text-xs text-muted"><strong className="text-text">Graph insights</strong><p className="mt-1">Most incoming: {(metrics.most_incoming||[]).slice(0,3).map(n=>`${n.label} (${n.incoming_count})`).join(' · ')||'Not available'}</p><p className="mt-1">Most outgoing: {(metrics.most_outgoing||[]).slice(0,3).map(n=>`${n.label} (${n.outgoing_count})`).join(' · ')||'Not available'}</p><p className="mt-1">Isolated modules: {(metrics.isolated_modules||[]).length}</p><p className="mt-1">Largest internal clusters: {(metrics.largest_internal_clusters||[]).slice(0,3).map(c=>`${c.size} modules`).join(' · ')||'None detected'}</p><p className="mt-1">External packages: {Object.entries(metrics.external_reference_counts||{}).sort((a,b)=>b[1]-a[1]).slice(0,4).map(([name,count])=>`${name} (${count})`).join(' · ')||'None detected'}</p></div>
   <div className="rounded-xl bg-raised p-3 text-xs text-muted">{selectedNode?<><strong className="text-text">{selectedNode.label}</strong><p className="mt-1 break-all">{selectedNode.path||'Third-party package'}</p><p>Incoming dependencies: {incoming.length} · Outgoing dependencies: {outgoing.length}</p><p className="mt-1">Incoming: {incoming.map(e=>e.source).join(', ')||'None detected'}</p><p>Outgoing: {outgoing.map(e=>e.target).join(', ')||'None detected'}</p></>:selectedEdge?<><strong className="text-text">Relationship details</strong><p className="mt-1 break-all">{selectedEdge.source} → {selectedEdge.target}</p><p>{selectedEdge.type} · {selectedEdge.confidence}</p><p>{selectedEdge.evidence}</p><p>{selectedEdge.source_path}{selectedEdge.line?`:${selectedEdge.line}`:''}</p></>:<span>Select a node or edge to inspect dependency evidence.</span>}</div></div>
  <p className="mt-2 text-xs text-muted">Solid arrows point from importing module to imported module. Purple = internal import; amber = external package. Graph display is capped at 180 filtered nodes for readability; backend limits and warnings describe any additional truncation.</p>
 </div>
}
function Workflow({ workflow }) {
 const workflows=workflow?.workflows||[]
 const [active,setActive]=useState(workflows[0]?.id||''),[selected,setSelected]=useState(null),[zoom,setZoom]=useState(1)
 const current=workflows.find(w=>w.id===active)||workflows[0]
 const steps=current?.steps||[],edges=current?.edges||[]
 const layout=useMemo(()=>{
  if(!steps.length)return {nodes:[],width:820,height:220}
  const W=198, GAP_X=104, GAP_Y=42, PAD=42
  const byId=new Map(steps.map((n,i)=>[n.id,{...n,_index:i}]))
  const valid=edges.filter(e=>byId.has(e.source)&&byId.has(e.target)&&e.type!=='loop-back')
  const indegree=new Map(steps.map(n=>[n.id,0])),out=new Map(steps.map(n=>[n.id,[]]))
  valid.forEach(e=>{indegree.set(e.target,(indegree.get(e.target)||0)+1);out.get(e.source).push(e.target)})
  const queue=steps.filter(n=>indegree.get(n.id)===0).map(n=>n.id)
  const level=new Map(steps.map(n=>[n.id,0])); let visited=0
  while(queue.length){const id=queue.shift();visited++;for(const target of out.get(id)){level.set(target,Math.max(level.get(target)||0,(level.get(id)||0)+1));indegree.set(target,indegree.get(target)-1);if(indegree.get(target)===0)queue.push(target)}}
  // Keep disconnected/cyclic nodes visible and in a stable order without allowing
  // loop-back edges to distort the acyclic execution layout.
  steps.forEach((n,i)=>{if(!valid.some(e=>e.target===n.id)&&!valid.some(e=>e.source===n.id)&&level.get(n.id)===0)level.set(n.id,i)})
  const buckets=new Map()
  steps.forEach(n=>{const col=level.get(n.id)||0;if(!buckets.has(col))buckets.set(col,[]);buckets.get(col).push(n)})
  const coords=[]
  for(const [col,items] of [...buckets.entries()].sort((a,b)=>a[0]-b[0])){
   items.sort((a,b)=>{
    const branch=(a.kind==='branch'?0:1)-(b.kind==='branch'?0:1)
    return branch || (a.order??a._index)-(b.order??b._index)
   })
   let y=PAD
   items.forEach((node,index)=>{
    const title=String(node.label||node.name||node.kind||'Step')
    const titleLines=Math.max(1,Math.ceil(title.length/25))
    const source=String(node.path||'')
    const sourceLines=source.length>48?2:(source?1:0)
    const h=Math.max(82,18+titleLines*17+sourceLines*13+20)
    coords.push({...node,x:PAD+Number(col)*(W+GAP_X),y,width:W,height:h,titleLines,sourceLines})
    y+=h+GAP_Y
   })
  }
  const maxY=Math.max(...coords.map(n=>n.y+n.height),PAD)
  return {nodes:coords,width:Math.max(820,...coords.map(n=>n.x+W+PAD)),height:maxY+PAD}
 },[steps,edges])
 const pos=Object.fromEntries(layout.nodes.map(n=>[n.id,n]))
 if(!current)return <Empty>Could not identify a supported application entry point or reconstruct a source-backed execution flow. The analyzer avoids fabricating a generic workflow.</Empty>
 const wrap=(text,max=25)=>{const words=String(text||'').split(/\s+/);const lines=[];let line='';for(const raw of words){let word=raw;while(word.length>max){if(line){lines.push(line);line=''}lines.push(word.slice(0,max));word=word.slice(max)}if((line+' '+word).trim().length>max&&line){lines.push(line);line=word}else line=(line+' '+word).trim()}if(line)lines.push(line);return lines}
 return <div>
  <div className="mb-3 flex flex-wrap items-center gap-3"><label className="text-sm text-muted" htmlFor="workflow-select">Workflow</label><select id="workflow-select" value={current.id} onChange={e=>{setActive(e.target.value);setSelected(null)}} className="min-w-0 flex-1 rounded-lg border border-line bg-raised px-3 py-2 text-sm text-text">{workflows.map(w=><option key={w.id} value={w.id}>{w.name}</option>)}</select><button className="control" onClick={()=>setZoom(v=>Math.min(1.8,v+.1))}>＋ Zoom</button><button className="control" onClick={()=>setZoom(v=>Math.max(.55,v-.1))}>－ Zoom</button><button className="control" onClick={()=>setZoom(1)}>Reset</button></div>
  <p className="mb-3 text-xs text-muted">{current.classification} · Entry: {current.entry_point?.path}:{current.entry_point?.line}</p>
  <div className="mb-3 flex flex-wrap gap-3 text-xs text-muted"><span>Click a step to inspect source evidence.</span><span>Teal = execution flow</span><span>Amber = decision</span><span>Purple = local function call</span><span>Scroll to navigate large workflows.</span></div>
  <div className="max-h-[720px] overflow-auto rounded-xl border border-line bg-[#0d1422] p-3">
   <svg viewBox={`0 0 ${layout.width} ${layout.height}`} width={layout.width*zoom} height={layout.height*zoom} role="img" aria-label={`Source-derived workflow ${current.name}`} style={{maxWidth:'none'}}>
    <defs><marker id="workflow-arrow-new" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0 0 L0 6 L8 3z" fill="#3fd5e8"/></marker></defs>
    {edges.map((edge,i)=>{const a=pos[edge.source],b=pos[edge.target];if(!a||!b)return null;const loop=edge.type==='loop-back';let d,labelX,labelY
      if(loop){const sx=a.x+a.width/2,sy=a.y,tx=b.x+b.width/2,ty=b.y;const lift=Math.max(24,Math.abs(sx-tx)*.18);d=`M ${sx} ${sy} C ${sx} ${sy-lift}, ${tx} ${ty-lift}, ${tx} ${ty}`;labelX=(sx+tx)/2;labelY=Math.min(sy,ty)-lift-4}
      else if(b.x>a.x){const sx=a.x+a.width,sy=a.y+a.height/2,tx=b.x,ty=b.y+b.height/2,mx=(sx+tx)/2;d=`M ${sx} ${sy} H ${mx} V ${ty} H ${tx}`;labelX=mx;labelY=(sy+ty)/2-7}
      else {const sx=a.x+a.width/2,sy=a.y,tx=b.x+b.width/2,ty=b.y+b.height;const lift=Math.max(24,Math.abs(sy-ty)*.2);d=`M ${sx} ${sy} C ${sx} ${sy-lift}, ${tx} ${ty+lift}, ${tx} ${ty}`;labelX=(sx+tx)/2;labelY=Math.min(sy,ty)-lift-4}
      return <g key={`${edge.source}-${edge.target}-${i}`}><path d={d} fill="none" stroke={edge.label==='False'?'#f59e0b':'#3fd5e8'} strokeWidth="2" markerEnd="url(#workflow-arrow-new)" strokeDasharray={loop?'5 4':undefined}/>{edge.label&&<text x={labelX} y={labelY} fill="#fcd34d" fontSize="11" textAnchor="middle"><tspan>{edge.label}</tspan></text>}</g>})}
    {layout.nodes.map(n=>{const isDecision=n.kind==='decision'||n.kind==='loop',isTerminal=n.kind==='end'||n.kind==='error',isCall=n.kind==='call';const fill=isDecision?'#473719':isCall?'#30234d':isTerminal?'#173b43':'#1b2941';const stroke=selected?.id===n.id?'#fbbf24':isDecision?'#f59e0b':isCall?'#a78bfa':isTerminal?'#2dd4bf':'#64748b';const titleLines=wrap(n.label,25);const shortPath=String(n.path||'');const displayPath=shortPath.length>48?`${shortPath.slice(0,22)}…${shortPath.slice(-22)}`:shortPath;return <g key={n.id} onClick={()=>setSelected(n)} style={{cursor:'pointer'}}>
     {isDecision?<polygon points={`${n.x+n.width/2},${n.y} ${n.x+n.width},${n.y+n.height/2} ${n.x+n.width/2},${n.y+n.height} ${n.x},${n.y+n.height/2}`} fill={fill} stroke={stroke} strokeWidth={selected?.id===n.id?3:1.7}/>:<rect x={n.x} y={n.y} width={n.width} height={n.height} rx="9" fill={fill} stroke={stroke} strokeWidth={selected?.id===n.id?3:1.7}/>}
     <text x={n.x+n.width/2} y={n.y+27} textAnchor="middle" fill="#f8fafc" fontSize="12" fontWeight="700">{titleLines.map((line,i)=><tspan key={i} x={n.x+n.width/2} dy={i===0?0:15}>{line}</tspan>)}</text>
     {displayPath&&<text x={n.x+n.width/2} y={n.y+n.height-12} textAnchor="middle" fill="#cbd5e1" fontSize="9"><tspan>{displayPath}{n.line?`:${n.line}`:''}</tspan></text>}
     <title>{`${n.label}\n${n.path||''}:${n.line||''}\n${n.evidence||''}`}</title>
    </g>})}
   </svg>
  </div>
  {selected&&<div className="mt-3 rounded-xl border border-line bg-raised p-4"><div className="flex justify-between gap-3"><strong className="text-text">{selected.label}</strong><button className="text-sm text-accent" onClick={()=>setSelected(null)}>Clear</button></div><p className="mt-1 break-all text-sm text-muted">{selected.path}:{selected.line}–{selected.end_line} · {selected.kind} · {selected.confidence}</p><p className="mt-2 whitespace-pre-wrap text-sm text-text">{selected.evidence}</p></div>}
  <p className="mt-3 text-xs text-muted">{(current?.limitations||workflow?.limitations||[]).join(' ')}</p>
 </div>
}

export default function AdvancedVisualizations({ data }) {
 const v=data?.advanced_visualizations
 if(!v)return <Panel title="Advanced Visualizations"><Empty>Visualization data was unavailable for this analysis. Existing dashboard results are unaffected.</Empty></Panel>
 const langs=v.languages||[],exts=v.extensions||[],tech=v.technologies||[]
 return <div className="space-y-4">
  {v.warnings?.length>0&&<div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 text-sm text-text"><strong>Analysis notes</strong><ul className="mt-1 list-disc pl-5">{v.warnings.map((w,i)=><li key={i}>{w}</li>)}</ul></div>}
  <Panel title="Repository Structure" note="Generated from the cloned repository. Secret files and generated/vendor folders are excluded."><div className="max-h-[520px] overflow-auto rounded-xl bg-raised p-2"><TreeNode node={v.tree}/></div><p className="mt-2 text-xs text-muted">{fmt(v.summary?.total_files)} files · {fmt(v.summary?.total_directories)} directories · bounded scan</p></Panel>
  <Panel title="Technology Stack"><div className="flex flex-wrap gap-2">{tech.length?tech.map((t,i)=><span key={`${t.name}-${i}`} className="rounded-full border border-line bg-raised px-3 py-2 text-sm text-text"><strong>{t.name}</strong><span className="ml-2 text-xs text-muted">{t.category}</span><span className="block text-[10px] text-muted">{t.evidence}</span></span>):<Empty/>}</div></Panel>
  <div className="grid gap-4 lg:grid-cols-2"><Panel title="Programming Language Distribution" note="Counts source files by recognized extension, not lines of code.">{langs.length?<><div className="h-64"><ResponsiveContainer><PieChart><Pie data={langs} dataKey="count" nameKey="name" innerRadius={55} outerRadius={90}>{langs.map((x,i)=><Cell key={x.name} fill={COLORS[i%COLORS.length]}/>)}</Pie><Tooltip {...TOOLTIP} formatter={(n,name,p)=>[`${fmt(n)} (${p.payload.percentage}%)`,name]}/></PieChart></ResponsiveContainer></div><p className="text-sm text-muted">{fmt(v.summary?.total_source_files)} recognized source files</p><div className="flex flex-wrap gap-3 text-xs text-text">{langs.map((l,i)=><span key={l.name}><i className="mr-1 inline-block h-2 w-2 rounded-full" style={{background:COLORS[i%COLORS.length]}}/>{l.name}: {l.percentage}% ({l.count})</span>)}</div></>:<Empty/>}</Panel>
  <Panel title="File Extension Distribution">{exts.length?<div className="h-72"><ResponsiveContainer><BarChart data={exts.slice(0,18)} layout="vertical" margin={{left:10}}><CartesianGrid stroke="#334155" horizontal={false}/><XAxis type="number" stroke="#cbd5e1" allowDecimals={false}/><YAxis type="category" dataKey="name" stroke="#e2e8f0" width={95}/><Tooltip {...TOOLTIP} formatter={(n,name,p)=>[`${fmt(n)} (${p.payload.percentage}%)`,name]}/><Bar dataKey="count" fill="#a78bfa"/></BarChart></ResponsiveContainer></div>:<Empty/>}</Panel></div>
  <Panel title="Dependency Graph" note="Directed imports: source module → imported module."><DependencyGraph graph={v.dependency_graph}/></Panel>
  <Panel title="Dynamic Architecture Diagram" note={v.architecture?.method}><Architecture architecture={v.architecture}/></Panel>
  <Panel title="Repository Workflow" note={v.workflow?.label}><Workflow workflow={v.workflow}/></Panel>
 </div>
}
