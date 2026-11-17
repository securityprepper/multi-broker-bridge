"use strict";
let data=null,view="positions",selected=new Set(),known=new Set(),lastRows=[],deferredInstall=null;
const $=id=>document.getElementById(id), esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const valid=n=>typeof n==="number"&&Number.isFinite(n), money=n=>valid(n)?n.toLocaleString("en-US",{style:"currency",currency:"USD",maximumFractionDigits:2}):"—";
const num=n=>valid(n)?n.toLocaleString("en-US",{maximumFractionDigits:4}):"—", pct=n=>valid(n)?(n>0?"+":"")+n.toFixed(2)+"%":"—", cls=n=>!valid(n)?"unknown":n>0?"positive":n<0?"negative":"";
const move=n=>'<span class="'+cls(n)+'">'+pct(n)+'</span>', tm=t=>t?new Date(t).toLocaleString("en-US",{timeZone:"America/Chicago",month:"short",day:"numeric",hour:"numeric",minute:"2-digit",second:"2-digit"}):"Unavailable";
const account=id=>data.accounts.find(a=>a.id===id)?.label||id;
const staleAccount=id=>{let a=data.accounts.find(x=>x.id===id);return !a?.asof||Date.now()-Date.parse(a.asof)>20*60000;};
function remember(){localStorage.setItem("sp-trading-filters-v1",JSON.stringify({selected:[...selected],paper:$("paper").checked,broker:$("broker").value,source:$("source").value,sector:$("sector").value,sort:$("sort").value}));}
function populate(id,values){const el=$(id),previous=el.value;el.replaceChildren(el.options[0]);for(const val of [...new Set(values)].filter(Boolean).sort()){const opt=document.createElement("option");opt.value=val;opt.textContent=val;el.append(opt);}el.value=previous;}
function setup(){
 let saved={};try{saved=JSON.parse(localStorage.getItem("sp-trading-filters-v1")||"{}");}catch{}
 populate("broker",data.accounts.map(a=>a.broker));populate("source",[...data.positions,...data.closed].map(p=>p.source));populate("sector",data.watch.map(p=>p.sector));
 if(!known.size){$("paper").checked=!!saved.paper;for(const k of ["broker","source","sector","sort"])if(saved[k])$(k).value=saved[k];}
 for(const a of data.accounts){if(!known.has(a.id)){if(!saved.selected||saved.selected.includes(a.id))selected.add(a.id);known.add(a.id);}}
 $("accounts").replaceChildren();
 for(const a of data.accounts){const label=document.createElement("label"),input=document.createElement("input");input.type="checkbox";input.checked=selected.has(a.id);input.setAttribute("aria-label",a.label);input.onchange=()=>{input.checked?selected.add(a.id):selected.delete(a.id);remember();render();};label.append(input,document.createTextNode(a.label));$("accounts").append(label);}
}
function filter(rows){return rows.filter(p=>selected.has(p.account)&&($("paper").checked||!p.paper)&&(!$("broker").value||p.broker===$("broker").value)&&(!$("source").value||p.source===$("source").value)&&matches(p));}
function matches(p){return p.symbol.toUpperCase().includes($("search").value.trim().toUpperCase())&&(!$("sector").value||(p.sector||data.watch.find(x=>x.symbol===p.symbol)?.sector)===$("sector").value);}
function sort(rows){let key=$("sort").value;return [...rows].sort((a,b)=>key==="symbol"?a.symbol.localeCompare(b.symbol):(b.changes?.[key]??b[key]??-Infinity)-(a.changes?.[key]??a[key]??-Infinity));}
function render(){
 if(!data)return;
 renderStops();
 const pos=sort(filter(data.positions)),closed=sort(filter(data.closed)),priced=pos.filter(p=>valid(p.pnl)),matched=closed.filter(p=>valid(p.pnl));
 const up=priced.reduce((s,p)=>s+p.pnl,0),rp=matched.reduce((s,p)=>s+p.pnl,0),wins=matched.filter(p=>p.pnl>0).length;
 $("unrealized").textContent=priced.length?money(up):"—";$("unrealized").className=cls(priced.length?up:null);
 $("realized").textContent=matched.length?money(rp):"—";$("realized").className=cls(matched.length?rp:null);
 $("winrate").textContent=matched.length?(wins/matched.length*100).toFixed(0)+"%":"—";$("count").textContent=pos.length;
 $("openDetail").textContent=priced.length+" priced · "+(pos.length-priced.length)+" missing · "+pos.filter(p=>p.stale).length+" old/missing prices · "+pos.filter(p=>staleAccount(p.account)).length+" old position snapshots";
 $("closedDetail").textContent=closed.length+" exits · "+(closed.length-matched.length)+" unmatched";$("winDetail").textContent=wins+" profitable / "+matched.length+" matched exits";
 const activeAccounts=data.accounts.filter(a=>selected.has(a.id)&&($("paper").checked||!a.paper)&&(!$("broker").value||a.broker===$("broker").value));
 $("coverage").textContent=activeAccounts.filter(a=>a.complete).length+" / "+activeAccounts.length+" accounts with complete positions";
 $("openBadge").textContent=pos.length;$("closedBadge").textContent=closed.length;
 const age=Date.now()-Date.parse(data.generated_at||0),fresh=age<180000&&data.gate==="UNPAUSED";
 $("live").textContent=data.gate!=="UNPAUSED"?data.gate.replaceAll("_"," "):fresh?"AUTO REFRESH":"SNAPSHOT STALE";$("live").className="pill"+(fresh?"":" warn");
 $("updated").textContent="Snapshot "+tm(data.generated_at)+" CT · Refreshes every minute · "+(data.day||"");
 let messages=[];
 if(data.gate!=="UNPAUSED")messages.push("Collection "+data.gate.toLowerCase().replaceAll("_"," ")+". Showing the last snapshot. Next check "+tm(data.next_check_at)+" CT.");
 if(age>=180000)messages.push("Dashboard data is stale. Last snapshot "+tm(data.generated_at)+" CT.");
 if(activeAccounts.some(a=>!a.complete))messages.push("Selected accounts have incomplete coverage. Totals cover the records shown.");
 $("message").hidden=!messages.length;$("message").textContent=messages.join(" ");
 let rows=pos,title="Open positions",help="Completed-bar changes: 1m, 5m, 10m, 20m, 30m, 1h, 2h, 4h and trading day.";
 if(view==="closed"){rows=closed;title="Closed today";help="Chicago trading date · FIFO-matched long exits · recorded fees only.";}
 if(view==="watch"){rows=sort(data.watch.filter(matches));title="Quality watchlist";help="All followed sectors · account, PAPER and source filters apply to position views.";}
 if(view==="sources"){title="Source performance";help="Selected accounts and closed exits today · verified order linkage; other fills remain Unattributed.";rows=closed;}
 $("viewTitle").textContent=title;$("viewHelp").textContent=help;lastRows=rows;
 $("content").innerHTML=view==="sources"?sources(rows):rows.length?table(rows)+(view==="positions"||view==="watch"?rows.map(card).join(""):""):'<div class="empty">No '+(view==="closed"?"closed trades today":view==="watch"?"watchlist symbols":"open positions")+' match these filters.</div>';
 $("health").innerHTML=data.accounts.map(a=>'<article><strong>'+esc(a.label)+'</strong><span class="'+(!a.complete?"stale":"")+'">'+esc(a.status)+'</span><small>'+esc(tm(a.asof))+' CT</small></article>').join("");
 $("notes").innerHTML=[...(data.issues||[]),...(data.notes||[])].map(s=>"<li>"+esc(s)+"</li>").join("");$("issueCount").textContent="· "+(data.issues||[]).length+" notices";
}
const windows=[["1","1m"],["5","5m"],["10","10m"],["20","20m"],["30","30m"],["60","1h"],["120","2h"],["240","4h"],["day","Day"],["open","Open"]];
function priceCell(p){return money(p.price)+'<small class="'+(p.stale?"stale":"")+'">'+(p.stale?"PRICE STALE · ":"")+esc(tm(p.price_asof||p.asof))+' CT</small>';}
function table(rows){
 if(view==="closed")return '<div class="table-wrap"><table><thead><tr>'+["Symbol","Account / source","Qty","Entry","Exit","P/L","P/L %","Exit time / basis"].map(x=>"<th>"+x+"</th>").join("")+'</tr></thead><tbody>'+rows.map(p=>'<tr><td><strong>'+esc(p.symbol)+'</strong></td><td>'+esc(account(p.account))+'<small>'+esc(p.source)+'</small></td><td>'+num(p.qty)+'</td><td>'+money(p.entry)+'</td><td>'+money(p.exit)+'</td><td class="'+cls(p.pnl)+'">'+money(p.pnl)+'</td><td>'+move(p.pct)+'</td><td>'+esc(tm(p.time))+' CT<small>'+esc(p.basis_status)+'</small></td></tr>').join("")+'</tbody></table></div>';
 const watch=view==="watch";
 return '<div class="table-wrap '+view+'"><table><thead><tr>'+["Symbol",watch?"Sector":"Account / source",...(watch?[]:["Qty","Entry"]),"Price",...(watch?[]:["Open P/L","P/L %"]),...windows.map(x=>x[1])].map(x=>"<th>"+x+"</th>").join("")+'</tr></thead><tbody>'+rows.map(p=>'<tr><td><strong>'+esc(p.symbol)+'</strong>'+((!watch&&staleAccount(p.account))?'<span class="tag">POSITION STALE</span>':'')+'<small>'+esc(p.detail||p.sector)+'</small></td><td>'+esc(watch?p.sector:account(p.account))+(watch?"":'<small>'+esc(p.source)+'</small>')+'</td>'+(watch?"":'<td>'+num(p.qty)+'</td><td>'+money(p.entry)+'</td>')+'<td>'+priceCell(p)+'</td>'+(watch?"":'<td class="'+cls(p.pnl)+'">'+money(p.pnl)+'</td><td>'+move(p.pct)+'</td>')+windows.map(([k])=>'<td>'+move(p.changes?.[k])+'</td>').join("")+'</tr>').join("")+'</tbody></table></div>';
}
function card(p){
 const watch=view==="watch";
 return '<article class="mobile-card"><div class="card-head"><div><strong>'+esc(p.symbol)+'</strong>'+((!watch&&staleAccount(p.account))?'<span class="tag">POSITION STALE</span>':'')+'<small>'+esc(watch?p.sector:account(p.account))+'</small></div><div class="price">'+priceCell(p)+'</div></div><div class="card-body">'+(watch?"":'<div><span>QUANTITY</span><b>'+num(p.qty)+'</b></div><div><span>ENTRY</span><b>'+money(p.entry)+'</b></div><div><span>OPEN P/L</span><b class="'+cls(p.pnl)+'">'+money(p.pnl)+'</b></div><div><span>P/L %</span><b>'+move(p.pct)+'</b></div>')+windows.map(([k,l])=>'<div><span>'+l.toUpperCase()+'</span><b>'+move(p.changes?.[k])+'</b></div>').join("")+'</div><div class="card-foot">'+esc(watch?p.sector:p.source+" · "+p.detail)+'</div></article>';
}
function sources(rows){
 const groups={};for(const p of rows){let g=groups[p.source]??={source:p.source,exits:0,matched:0,wins:0,pnl:0,sumPct:0};g.exits++;if(valid(p.pnl)){g.matched++;g.wins+=p.pnl>0;g.pnl+=p.pnl;g.sumPct+=p.pct||0;}}
 if(!Object.keys(groups).length)return '<div class="empty">No closed trades match these filters today.</div>';
 return '<div class="table-wrap"><table><thead><tr>'+["Order source","Exits / matched","Win rate","Average P/L %","Net P/L"].map(x=>"<th>"+x+"</th>").join("")+'</tr></thead><tbody>'+Object.values(groups).sort((a,b)=>b.pnl-a.pnl).map(g=>'<tr><td><strong>'+esc(g.source)+'</strong></td><td>'+g.exits+" / "+g.matched+'</td><td>'+pct(g.matched?g.wins/g.matched*100:null)+'</td><td>'+move(g.matched?g.sumPct/g.matched:null)+'</td><td class="'+cls(g.matched?g.pnl:null)+'">'+money(g.matched?g.pnl:null)+'</td></tr>').join("")+'</tbody></table></div>';
}
async function refresh(){try{const response=await fetch("/trading/api/dashboard",{cache:"no-store",credentials:"same-origin"});if(!response.ok)throw Error("Snapshot unavailable ("+response.status+")");data=await response.json();setup();render();}catch(e){$("message").hidden=false;$("message").textContent="Refresh failed. "+(data?"Showing the last loaded snapshot. ":"")+e.message;$("live").textContent="DISCONNECTED";$("live").className="pill warn";}}
for(const id of ["broker","source","paper","sector","sort"])$(id).addEventListener("change",()=>{remember();render();});
$("search").addEventListener("input",render);
$("refresh").onclick=refresh;$("reset").onclick=()=>{for(const id of ["broker","source","sector","search"])$(id).value="";$("sort").value="symbol";$("paper").checked=false;selected=new Set(data.accounts.map(a=>a.id));remember();setup();render();};
document.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>{view=b.dataset.view;document.querySelectorAll("[data-view]").forEach(x=>x.classList.toggle("active",x===b));render();});
$("export").onclick=()=>{const fields=view==="closed"||view==="sources"?["symbol","broker","account","paper","source","qty","entry","exit","pnl","pct","time","basis_status"]:["symbol","broker","account","paper","source","sector","qty","entry","price","pnl","pct","price_asof","stale",...windows.map(x=>x[0])];const quote=x=>'"'+String(x??"").replaceAll('"','""')+'"';const csv=[fields,...lastRows.map(p=>fields.map(k=>{let v=p[k]??p.changes?.[k]??"";return typeof v==="string"&&/^[=+\-@\t\r]/.test(v)?"'"+v:v;}))].map(row=>row.map(quote).join(",")).join("\r\n");const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));const a=document.createElement("a");a.href=url;a.download="trading-"+view+"-"+data.day+".csv";a.click();URL.revokeObjectURL(url);};
window.addEventListener("beforeinstallprompt",e=>{e.preventDefault();deferredInstall=e;$("install").hidden=false;});$("install").onclick=async()=>{if(deferredInstall){await deferredInstall.prompt();deferredInstall=null;$("install").hidden=true;}};
if("serviceWorker" in navigator)navigator.serviceWorker.register("/trading/sw.js",{scope:"/trading/"}).catch(()=>{});
refresh();setInterval(()=>{if(!document.hidden)refresh();},60000);document.addEventListener("visibilitychange",()=>{if(!document.hidden)refresh();});

function renderStops(){
 const w=data.stop_watch;
 if(!w){$("stopStatus").textContent="Not yet checked. Live closing disabled.";return;}
 const stale=Date.now()-Date.parse(w.checked_at)>180000||data.gate!=="UNPAUSED";
 $("stopStatus").textContent="REPORT ONLY · Live closing disabled · "+w.session+" · Checked "+tm(w.checked_at)+" CT"+(stale?" · STALE":"")+". "+(w.coverage||[]).map(c=>c.broker+": "+c.status).join(" · ");
 const entries=w.entries||[];$("stopEntries").hidden=!entries.length&&!$("paper").checked;
 $("stopEntries").innerHTML=entries.map(e=>'<article class="stop-card"><strong>'+esc(e.symbol)+' · '+esc(e.broker)+'</strong><p>'+esc(account(e.account))+' · '+num(e.qty)+' shares · Stop '+money(e.stop)+' · Price '+money(e.price)+' · <span class="negative">'+pct(-e.below_pct)+' below stop</span></p><small>Quote '+esc(tm(e.price_asof))+' CT · Order '+esc(e.id)+' · '+esc(stale?"STALE EVIDENCE — refresh required":e.status)+'</small></article>').join("");
 if($("paper").checked){$("stopEntries").innerHTML+='<p class="muted">PAPER commissioning</p>'+(w.paper_tests||[]).map(t=>'<p>'+esc(t.broker)+' · <strong>'+esc(t.status)+'</strong> · '+esc(tm(t.updated))+' CT</p>').join("");}
}