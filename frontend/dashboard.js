const $ = (id) => document.getElementById(id);
let tickets = [];
let selectedTicket = null;
const savedKey = sessionStorage.getItem("grievance_api_key") || "";
$("apiUrl").value = window.location.origin.startsWith("http") ? window.location.origin : "http://127.0.0.1:8000";
$("apiKey").value = savedKey;

function apiBase(){ return $("apiUrl").value.trim().replace(/\/+$/,""); }
function headers(json=true){ const h={"X-API-Key":$("apiKey").value.trim()}; if(json) h["Content-Type"]="application/json"; return h; }
async function request(path, options={}) {
  const response = await fetch(apiBase()+path,{...options,headers:{...headers(options.body!==undefined),...(options.headers||{})}});
  const raw=await response.text(); let data; try{data=raw?JSON.parse(raw):{};}catch{data=raw;}
  if(!response.ok) throw new Error((data && data.detail) || `Request failed (${response.status})`);
  return data;
}
function toast(message,error=false){const el=$("toast");el.textContent=message;el.className="toast show"+(error?" error":"");setTimeout(()=>el.className="toast",3200);}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function date(v){if(!v)return "—";const d=new Date(Number(v)*1000);return isNaN(d)?esc(v):d.toLocaleString();}
function statusLabel(s){return ({needs_review:"Needs review",new:"Ready to resolve",resolved:"Resolved"})[s]||s||"Unknown";}
function render(){
  $("totalCount").textContent=tickets.length;
  $("reviewCount").textContent=tickets.filter(t=>t.status==="needs_review").length;
  $("newCount").textContent=tickets.filter(t=>t.status==="new").length;
  $("resolvedCount").textContent=tickets.filter(t=>t.status==="resolved").length;
  const q=$("searchInput").value.toLowerCase(), status=$("statusFilter").value;
  const filtered=tickets.filter(t=>(status==="all"||t.status===status)&&[t.id,t.category,t.priority,t.source,t.text].join(" ").toLowerCase().includes(q));
  $("ticketRows").innerHTML=filtered.length?filtered.map(t=>`<tr>
    <td><div class="case-id">#GR-${String(t.id).padStart(4,"0")}</div><div class="case-date">${date(t.created)}</div></td>
    <td>${esc(t.category||"Unclassified")}</td>
    <td><span class="pill p-${esc((t.priority||"low").toLowerCase())}">${esc(t.priority||"—")}</span></td>
    <td><span class="confidence">${Math.round((Number(t.confidence)||0)*100)}%</span></td>
    <td><span class="pill s-${esc(t.status)}">${esc(statusLabel(t.status))}</span></td>
    <td>${esc(t.source||"—")}</td><td><button class="view-btn" data-id="${t.id}">View details →</button></td></tr>`).join(""):`<tr><td colspan="7" class="empty">No grievances match this filter.</td></tr>`;
  document.querySelectorAll("[data-id]").forEach(b=>b.addEventListener("click",()=>openTicket(Number(b.dataset.id))));
}
async function connect(){
  $("connection").className="connection";$("connection").lastElementChild.textContent="Connecting…";
  try{
    const health=await fetch(apiBase()+"/health").then(r=>{if(!r.ok)throw Error("Health check failed");return r.json();});
    sessionStorage.setItem("grievance_api_key",$("apiKey").value.trim());
    await loadTickets();
    $("connection").className="connection online";$("connection").lastElementChild.textContent="API connected";
    $("kbStatus").textContent=`Knowledge base: ${health.kb_chunks??"—"} chunks`;
    $("lastUpdated").textContent="Updated "+new Date().toLocaleTimeString();
    toast("Dashboard connected successfully.");
  }catch(e){$("connection").className="connection offline";$("connection").lastElementChild.textContent="Connection failed";toast(e.message+" — check API URL and API key.",true);}
}
async function loadTickets(){tickets=await request("/tickets?limit=200");render();$("lastUpdated").textContent="Updated "+new Date().toLocaleTimeString();}
async function openTicket(id){
  try{
    selectedTicket=await request(`/tickets/${id}`);
    const t=selectedTicket;
    $("modalTitle").textContent=`Grievance #GR-${String(t.id).padStart(4,"0")}`;
    $("modalBody").innerHTML=`<div class="detail-grid">
      <div class="detail-box"><small>Category</small><b>${esc(t.category)}</b></div>
      <div class="detail-box"><small>Priority</small><b>${esc(t.priority)}</b></div>
      <div class="detail-box"><small>Confidence</small><b>${Math.round((Number(t.confidence)||0)*100)}%</b></div>
      <div class="detail-box"><small>Status</small><b>${esc(statusLabel(t.status))}</b></div>
      <div class="detail-box"><small>Source</small><b>${esc(t.source)}</b></div>
      <div class="detail-box"><small>Received</small><b>${date(t.created)}</b></div></div>
      <div class="detail-block"><h3>GRIEVANCE MESSAGE</h3><p>${esc(t.text)}</p></div>
      <div class="detail-block"><h3>AI-GENERATED RESPONSE · EDIT BEFORE APPROVAL</h3><textarea class="reply-editor" id="replyEditor">${esc(t.reply||"")}</textarea></div>
      ${t.status==="resolved"?"<p class='muted'>This ticket is already marked as resolved.</p>":`<div class="modal-actions"><button class="btn btn-dark" id="closeTicket">Close</button><button class="btn btn-primary" id="approveBtn">Approve & resolve</button></div>`}`;
    $("ticketModal").classList.remove("hidden");
    $("closeTicket")?.addEventListener("click",closeModal);
    $("approveBtn")?.addEventListener("click",approveTicket);
  }catch(e){toast(e.message,true);}
}
function closeModal(){$("ticketModal").classList.add("hidden");}
async function approveTicket(){
  if(!selectedTicket)return;
  const reply=$("replyEditor").value.trim();if(!reply){toast("Please enter a response before approval.",true);return;}
  if(!confirm("Approve this response and mark the grievance as resolved? For Gmail tickets, this sends an email reply."))return;
  try{await request(`/tickets/${selectedTicket.id}/approve`,{method:"POST",body:JSON.stringify({reply})});closeModal();await loadTickets();toast("Ticket approved and marked resolved.");}
  catch(e){toast(e.message,true);}
}
$("connectBtn").addEventListener("click",connect);
$("refreshBtn").addEventListener("click",()=>loadTickets().then(()=>toast("Dashboard refreshed.")).catch(e=>toast(e.message,true)));
$("searchInput").addEventListener("input",render);$("statusFilter").addEventListener("change",render);
$("closeModal").addEventListener("click",closeModal);
$("ticketModal").addEventListener("click",e=>{if(e.target===$("ticketModal"))closeModal();});
$("grievanceForm").addEventListener("submit",async e=>{
  e.preventDefault();const text=$("grievanceText").value.trim();if(text.length<3)return;
  const btn=e.submitter;btn.disabled=true;btn.textContent="Analyzing…";
  try{const result=await request("/grievance",{method:"POST",body:JSON.stringify({text,source:"dashboard"})});$("grievanceText").value="";await loadTickets();toast(`Grievance analyzed. Ticket #${result.id} created.`);openTicket(result.id);}
  catch(err){toast(err.message,true);}finally{btn.disabled=false;btn.innerHTML='Analyze grievance <span>→</span>';}
});
connect();
