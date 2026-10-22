/* global Api, ConfirmDialog */
/** Vanilla editor owns drafts and transport; all timing/geometry/approval rules stay server-side. */
const ExplainerEditor = (() => {
  const escape = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  // Phase 59 (ENH-041): the VOX kinds, and a ready outside-AI prompt for a segment's picture in the VOX collage style
  const VOX_KINDS = ["quote","text_card","diagram","chart","timeline","map","activity","photo"];
  const SOLO_KINDS = ["activity","photo","diagram","text_card"];
  function voxPicturePrompt(segment, topic, sceneName, style = "vox") {
    // Phase 63 (ENH-045): a news Short wants a realistic vertical news photo; a blur Short a calm vertical backdrop
    if (style === "news") return `Realistic news photograph for an English news short about "${topic}": ${segment.intent}.`
      + `${sceneName ? ` Setting: ${sceneName}.` : ""} Natural light, documentary style, one clear subject, 9:16 vertical portrait.`
      + " No text, no letters, no logos, no watermark, no real famous people, no recognisable faces.";
    if (["blur", "mistakes", "wordday", "top5", "quiz", "listen"].includes(style)) return `Atmospheric background photo for a short inspirational video about "${topic}": ${segment.intent}.`
      + " Soft colours, simple shapes, plenty of empty space, 9:16 vertical portrait. No text, no logos, no people's faces.";
    return `Editorial paper-collage illustration for an explainer video about "${topic}": ${segment.intent}.`
      + `${sceneName ? ` Setting: ${sceneName}.` : ""} Cut-out photo elements on warm off-white paper, muted warm colours with one red accent,`
      + " soft shadows, simple clear composition with space around the main subject, 16:9 landscape. No text, no letters, no logos, no watermark,"
      + " no real famous people.";
  }
  async function mount(container, projectId, options = {}) {
    const SHORT_TITLES = {news:"English news Short",blur:"Text-on-blur Short",mistakes:"Don't say / Say Short",wordday:"Word of the day Short",top5:"Top 5 phrases Short",
      quiz:"Countdown quiz Short",listen:"Listening challenge Short"};
    const short = options.style in SHORT_TITLES;  // Phase 63/64: the Shorts are voice-only like VOX
    const vox = short || options.style === "vox";
    const title = short ? SHORT_TITLES[options.style] : vox ? "VOX explainer" : "Solo Explainer";
    const state = {view:null,segments:[],assets:[],selected:0,aspect:short?"9:16":"16:9",dirty:false,edit:0,saving:null,busy:false,
      conflict:false,disposed:false,preview:null,previewToken:0,geometry:null,job:null,timer:null,stage:{scenes:[],activities:[]}};
    container.innerHTML = `<div class="solo-editor${vox?" is-vox":""}"><h2>${title}</h2>
      ${vox?`<p class="section-hint">Review the knowledge claims, the numbers on charts and the pictures. Nobody is on screen: the narrator's voice reads the script over the graphics.</p>
      <div class="vox-references"><strong>Reference pictures</strong><span class="section-hint">Upload pictures you made with an outside AI or took yourself; the next proposal uses them where they fit, and any segment can show one.</span>
        <label class="btn btn-ghost btn-sm">⬆ Upload pictures<input id="vox-references" type="file" accept="image/png,image/jpeg,image/webp" multiple hidden></label>
        <span id="vox-reference-count" class="section-hint"></span></div>`
      :`<p class="section-hint">Review knowledge claims, illustrations and both layouts. <a href="/characters">Create the 21 front presenter pictures in Character Library</a>.</p>`}
      <div class="solo-toolbar"><button type="button" data-action="propose" class="btn btn-primary">Propose plan</button>
      <button type="button" data-action="save" class="btn btn-ghost">Save changes</button>${vox?"":`<button type="button" data-action="arrange" class="btn btn-ghost">Arrange layouts</button>`}
      <button type="button" data-action="preview" class="btn btn-ghost">Refresh preview</button><button type="button" data-action="approve" class="btn btn-primary">Approve reviewed plan</button>
      <button type="button" data-action="reload" class="btn btn-ghost">Reload</button><button type="button" data-action="cancel" class="btn btn-ghost" hidden>Cancel proposal</button>
      <label>Preview aspect <select id="solo-aspect">${short?"":"<option>16:9</option>"}<option>9:16</option></select></label></div>
      <p id="solo-status" role="status"></p><p id="solo-error" role="alert"></p><ul id="solo-issues"></ul>
      <div class="solo-editor-grid"><div><div id="solo-player"></div><div id="solo-segments" class="solo-segments"></div></div>
      <div id="solo-fields" class="solo-fields"></div></div></div>`;
    const $ = id => container.querySelector(`#${id}`);
    const message = (text,error=false) => {if(!state.disposed) $(error?"solo-error":"solo-status").textContent=text;};
    function controls() {
      container.querySelectorAll("[data-action]").forEach(button=>{
        const action=button.dataset.action;
        button.disabled=state.busy || (state.conflict && !["reload","cancel"].includes(action)) || (!state.view?.plan && !["propose","reload","cancel"].includes(action));
        if(action==="cancel") {button.hidden=!state.job;button.disabled=!state.job;}
      });
      container.querySelectorAll("#solo-fields input,#solo-fields textarea,#solo-fields select,#solo-aspect,[data-segment]").forEach(input=>{input.disabled=state.busy;});
    }
    function fail(error) {if(state.disposed)return;message(error.message,true);if(error.status===409){state.conflict=true;clearTimeout(state.timer);message("A newer revision exists. Your draft is retained here; review it before Reload.",true);}controls();}
    function render() {
      if(state.disposed)return;
      const plan=state.view?.plan;
      $("solo-status").textContent=plan?`Revision ${plan.revision} · ${plan.status}${state.dirty?" · unsaved changes":""}`:"No plan yet. Propose a plan after writing the script.";
      $("solo-issues").innerHTML=(state.view?.issues??[]).map(issue=>`<li>${escape(issue)}</li>`).join("");
      if(vox&&$("vox-reference-count"))$("vox-reference-count").textContent=state.assets.length?`${state.assets.length} picture${state.assets.length===1?"":"s"} in this project`:"";
      $("solo-segments").innerHTML=state.segments.map((segment,i)=>`<button type="button" data-segment="${i}" aria-pressed="${i===state.selected}">${i+1}. ${escape(segment.intent)}</button>`).join("");
      renderFields();controls();
    }
    function renderFields() {
      const s=state.segments[state.selected];if(!s){$("solo-fields").innerHTML="";return;}
      const v=s.visual,l=s.layouts[state.aspect];
      const textarea=(name,label,value,rows=3)=>`<label>${label}<textarea data-field="${name}" rows="${rows}">${escape(value)}</textarea></label>`;
      $("solo-fields").innerHTML=`<h3>Segment ${state.selected+1}</h3>
        ${textarea("intent","Idea / purpose",s.intent,2)}
        <label>${vox?"Scene (faded behind the graphics)":"Scene behind the presenter"} <select data-field="scene"><option value="">No scene (plain background)</option>${state.stage.scenes.map(item=>`<option value="${escape(item.id)}" ${s.scene?.scene_id===item.id?"selected":""}>${escape(item.name)} · ${escape(item.category||"")}</option>`).join("")}</select></label>
        <label>Visual type <select data-field="kind">${(vox?VOX_KINDS:SOLO_KINDS).map(kind=>`<option ${v.kind===kind?"selected":""}>${kind}</option>`).join("")}</select></label>
        ${vox?voxFields(s,v,textarea):""}
        ${v.kind==="activity"?`<label>Activity picture (full screen behind the presenter) <select data-field="activity"><option value="">Choose…</option>${state.stage.activities.map(item=>`<option value="${escape(item.id)}" ${v.activity_id===item.id?"selected":""}>${escape(item.activity)}${item.presenter_own?" · own":""}</option>`).join("")}</select></label>`:""}
        ${vox&&!["photo","activity","text_card","diagram"].includes(v.kind)?"":v.kind==="activity"?"":v.kind==="photo"?`<label>Project illustration <select data-field="asset"><option value="">Not selected</option>${state.assets.map((item,i)=>`<option value="${i}" ${v.asset?.asset_id===item.asset.asset_id?"selected":""}>${escape(item.filename)}</option>`).join("")}</select></label>
          <label>Import illustration <input id="solo-upload" type="file" accept="image/png,image/jpeg,image/webp"></label>
          ${textarea("prompt","Outside-AI illustration prompt",v.prompt??"")}
          <label>Photo framing <select data-field="fit"><option ${v.fit!=="cover"?"selected":""}>contain</option><option ${v.fit==="cover"?"selected":""}>cover</option></select></label>
          <p class="section-hint">Mark important areas by dragging over the illustration. Unmarked images are kept in a separate panel.</p>
          <div id="solo-annotation" class="solo-annotation">${v.asset?`<img draggable="false" src="${escape(state.assets.find(a=>a.asset.asset_id===v.asset.asset_id)?.preview_url??"")}" alt="Illustration protected areas">` : "Select an image first"}
          ${(v.important_regions??[]).map(r=>`<span style="left:${r.x*100}%;top:${r.y*100}%;width:${r.width*100}%;height:${r.height*100}%"></span>`).join("")}</div>
          <button type="button" data-action="clear-regions" class="btn btn-ghost">Clear marked areas</button>`:
          `${textarea("title","Title",v.title??"",2)}${v.kind==="text_card"?textarea("bullets","One bullet per line",(v.bullets??[]).join("\n"))+textarea("emphasis","Emphasis",v.emphasis??"",1):
          `<label>Diagram template <select data-field="template">${["steps","comparison","cause_effect"].map(kind=>`<option ${v.template===kind?"selected":""}>${kind}</option>`).join("")}</select></label>${textarea("nodes","One node per line: label | detail",v.nodes.map(n=>`${n.label}${n.detail?` | ${n.detail}`:""}`).join("\n"),6)}`}`}
        ${textarea("source_notes","Sources / review notes",s.source_notes??"")}
        <label><input type="checkbox" data-field="reviewed" ${!s.needs_fact_review?"checked":""}> I checked the knowledge claims and illustration text</label>
        ${vox?"":`<fieldset><legend>${escape(state.aspect)} presenter placement</legend>${l?`
          <label>Anchor <select data-field="anchor">${["left","right","center"].map(a=>`<option ${l.presenter.anchor===a?"selected":""}>${a}</option>`).join("")}</select></label>
          ${["x","y","height"].map(key=>`<label>${key} <input data-field="${key}" type="number" step="0.01" min="${key==="height"?stageRange().min:0}" max="${key==="height"?stageRange().max:key==="y"?4:1}" value="${l.presenter[key]}"></label>`).join("")}
          <label>Transition <select data-field="transition">${["cut","ease","slide"].map(t=>`<option ${l.transition===t?"selected":""}>${t}</option>`).join("")}</select></label>`:"Arrange layouts after importing the approved front21 pack and generating audio."}</fieldset>
        <h4>Gestures anchored to actual speech</h4>${textarea("gestures","One cue per line: line_id | token_index | gesture",s.gestures.map(c=>`${c.at.line_id} | ${c.at.token_index} | ${c.gesture}`).join("\n"),3)}`}
        ${vox?picturePanel(s):""}
        <details><summary>Script anchors</summary><p>${escape(s.line_ids.join(" · "))}</p><p>Tokens ${s.start.token_index}–${s.end.token_index} (end exclusive)</p></details>
        <h4>Protected edits</h4>${Object.entries(s.locks).map(([key,locked])=>`<label><input type="checkbox" data-unlock="${key}" ${locked?"checked":""}> ${escape(key)}${locked?" (locked)":""}</label>`).join("")}`;
      let start=null;
      const area=$("solo-annotation");
      if(area?.querySelector("img")) {
        area.onpointerdown=e=>{if(state.busy)return;area.setPointerCapture(e.pointerId);const r=area.getBoundingClientRect();start={x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height};e.preventDefault();};
        area.onpointerup=e=>{if(!start)return;const r=area.getBoundingClientRect(),x=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),y=Math.max(0,Math.min(1,(e.clientY-r.top)/r.height));
          const box={x:Math.min(start.x,x),y:Math.min(start.y,y),width:Math.abs(x-start.x),height:Math.abs(y-start.y)};start=null;
          if(box.width>.01&&box.height>.01&&(s.visual.important_regions??[]).length<12){s.visual.important_regions??=[];s.visual.important_regions.push(box);changed();renderFields();}};
      }
    }
    // ---- Phase 59: VOX fields (line-based, like the diagram nodes) and the "Picture for this segment" panel
    function voxFields(s,v,textarea){
      if(v.kind==="quote")return `${textarea("text","Quote (shown word by word)",v.text??"",3)}${textarea("highlight","Highlighted words (part of the quote)",v.highlight??"",1)}${textarea("attribution","Who said it (optional)",v.attribution??"",1)}`;
      if(v.kind==="chart")return `${textarea("title","Title",v.title??"",1)}<label>Chart type <select data-field="chart_type">${["bar","line"].map(t=>`<option ${v.chart_type===t?"selected":""}>${t}</option>`).join("")}</select></label>
        ${textarea("unit","Unit (%, people, $…)",v.unit??"",1)}${textarea("items","One item per line: label | value (only numbers said in the narration)",(v.items??[]).map(i=>`${i.label} | ${i.value}`).join("\n"),5)}`;
      if(v.kind==="timeline")return `${textarea("title","Title",v.title??"",1)}${textarea("events","One event per line: when | what happened",(v.events??[]).map(e=>`${e.when} | ${e.label}`).join("\n"),5)}`;
      if(v.kind==="map")return `${textarea("title","Title",v.title??"",1)}${textarea("places","One place per line: name | latitude | longitude",(v.places??[]).map(p=>`${p.name} | ${p.lat} | ${p.lon}`).join("\n"),4)}
        ${textarea("highlight_countries","Countries to highlight (comma separated)",(v.highlight_countries??[]).join(", "),1)}
        ${textarea("route","Route between two places: from | to (place numbers, from 1; empty for none)",v.route?.length===2?`${v.route[0]+1} | ${v.route[1]+1}`:"",1)}`;
      return "";
    }
    function picturePanel(s){
      const scene=state.stage.scenes.find(item=>item.id===s.scene?.scene_id)?.name??"";
      const prompt=s.visual.kind==="photo"&&s.visual.prompt?s.visual.prompt:voxPicturePrompt(s,options.topic??"",scene,options.style);
      return `<fieldset class="vox-picture"><legend>Picture for this segment</legend>
        <p class="section-hint">Make it with an outside AI (ChatGPT, Gemini, Midjourney…) from this prompt, or use a picture of your own. The segment then shows it as a collage picture.</p>
        <textarea id="vox-picture-prompt" rows="5" readonly>${escape(prompt)}</textarea>
        <div class="library-actions"><button type="button" data-action="copy-picture-prompt" class="btn btn-ghost btn-sm">📋 Copy prompt</button>
        <label class="btn btn-primary btn-sm">⬆ Use my picture<input id="vox-picture-upload" type="file" accept="image/png,image/jpeg,image/webp" hidden></label></div></fieldset>`;
    }
    function changed(){state.dirty=true;state.edit++;clearTimeout(state.timer);message("Unsaved changes");if(!state.conflict)state.timer=setTimeout(()=>save().catch(fail),450);}
    async function save() {
      if(state.saving)return state.saving;if(!state.dirty||!state.view?.plan||state.conflict)return;
      state.saving=(async()=>{while(state.dirty&&!state.conflict&&!state.disposed){const edit=state.edit,segments=structuredClone(state.segments),unlock=structuredClone(state.unlock??{});
        const result=await Api.saveExplainerPlan(projectId,{expected_revision:state.view.plan.revision,expected_source_fingerprint:state.view.current_source_fingerprint,segments,aspects:state.view.plan.aspects,unlock_fields:unlock});
        if(state.disposed)return;state.view=result;
        if(state.edit===edit){state.segments=result.plan.segments;state.dirty=false;state.unlock={};
          if(!container.contains(document.activeElement)||!document.activeElement.matches("[data-field]"))render();
          else {message(`Revision ${result.plan.revision} · ${result.plan.status}`);controls();}}
        else {for(const segment of state.segments){const saved=result.plan.segments.find(s=>s.id===segment.id);if(saved)segment.locks=saved.locks;}}
      }})().finally(()=>{state.saving=null;});
      try{return await state.saving;}catch(error){fail(error);throw error;}
    }
    // Phase 55: the presenter's height range comes from the shared rules (stage proof), not fixed numbers.
    function stageRange(){const stage=state.rules?.aspects?.[state.aspect]?.stage;return {min:stage?.minHeight??.12,max:stage?.maxHeight??3};}
    async function reload(){const view=await Api.getExplainerPlan(projectId);if(state.disposed)return;state.view=view;state.segments=structuredClone(view.plan?.segments??[]);state.assets=await Api.listExplainerAssets(projectId);state.stage=await Api.getExplainerStageChoices(projectId).catch(()=>state.stage);
      state.rules??=await fetch("/static/explainer-layout-rules.json").then(response=>response.ok?response.json():null).catch(()=>null);state.selected=Math.min(state.selected,Math.max(0,state.segments.length-1));state.conflict=false;state.dirty=false;state.unlock={};render();}
    async function preview(){const token=++state.previewToken;const data=await Api.previewExplainerPlan(projectId,state.aspect);if(state.disposed||token!==state.previewToken)return;
      if(!window.SoloPreview)throw new Error("Preview bundle is missing. Rebuild the preview widget before starting the app.");
      state.geometry=data.props.solo.geometry;
      if(state.preview)state.preview.update(data.props);else state.preview=window.SoloPreview.mount($("solo-player"),data.props);
    }
    async function operate(action){if(state.busy||state.disposed)return;
      if(action==="reload"&&state.dirty&&!await ConfirmDialog.ask("Discard the local unsaved plan draft and load the server revision?",{confirmLabel:"Reload"}))return;
      state.busy=true;controls();
      try {if(action!=="reload")await save();if(state.conflict&&action!=="reload")return;message("Working…");$("solo-error").textContent="";
        if(action==="reload")await reload();
        if(action==="save")message("Plan saved");
        if(action==="arrange") {const result=await Api.arrangeExplainerPlan(projectId,{expected_revision:state.view.plan.revision,source_fingerprint:state.view.current_source_fingerprint});
          state.geometry=result.geometry;state.segments=result.segments;changed();await save();await preview();}
        if(action==="preview")await preview();
        if(action==="approve") {const result=await Api.approveExplainerPlan(projectId,{expected_revision:state.view.plan.revision,source_fingerprint:state.view.current_source_fingerprint});state.view=result;state.segments=result.plan.segments;render();await preview();}
        if(action==="propose") {const job=await Api.proposeExplainerPlan(projectId,{expected_revision:state.view?.plan?.revision??0});state.job=job;controls();
          for(let i=0;i<2400&&!state.disposed;i++){const current=await Api.getAiJob(projectId,job.id);message(`Proposal: ${current.stage} · ${current.progress}%`);
            if(["complete","error","cancelled","stale"].includes(current.status)){if(current.status!=="complete")throw new Error(current.error_message||`Proposal ${current.status}`);break;}
            if(i===2399)throw new Error("The proposal is still running. Reload later to resume its durable status.");await new Promise(resolve=>setTimeout(resolve,500));}
          state.job=null;await reload();}
      }catch(error){fail(error);}finally{state.job=null;state.busy=false;controls();
        if(!state.disposed&&!state.conflict&&!state.dirty&&!$("solo-error").textContent&&state.view?.plan)message(`Revision ${state.view.plan.revision} · ${state.view.plan.status}`);}}
    container.addEventListener("click",e=>{const selected=e.target.closest("[data-segment]");if(selected){state.selected=Number(selected.dataset.segment);render();return;}
      const action=e.target.closest("[data-action]")?.dataset.action;if(!action)return;
      if(action==="cancel"&&state.job){Api.cancelAiJob(projectId,state.job.id).catch(fail);return;}
      if(action==="clear-regions"){state.segments[state.selected].visual.important_regions=[];changed();renderFields();return;}
      if(action==="copy-picture-prompt"){const text=$("vox-picture-prompt")?.value??"";navigator.clipboard?.writeText(text).then(()=>message("Copied"),()=>{$("vox-picture-prompt").select();message("Clipboard unavailable",true);});return;}
      operate(action);});
    container.addEventListener("input",e=>{const field=e.target.dataset.field,s=state.segments[state.selected];if(!field||!s)return;
      const v=s.visual,value=e.target.value,l=s.layouts[state.aspect];
      if(["intent","source_notes"].includes(field))s[field]=value;
      else if(field==="reviewed")s.needs_fact_review=!e.target.checked;
      else if(field==="scene")s.scene=value?{scene_id:value}:null;
      else if(field==="activity"){v.activity_id=value;}
      else if(vox&&field==="items")v.items=value.split("\n").filter(Boolean).map(line=>{const [label,amount]=line.split("|").map(x=>x.trim());return{label:label||"?",value:Number(amount)||0};});
      else if(vox&&field==="events")v.events=value.split("\n").filter(Boolean).map(line=>{const [when,...rest]=line.split("|");return{when:(when??"").trim(),label:rest.join("|").trim()||"…"};});
      else if(vox&&field==="places")v.places=value.split("\n").filter(Boolean).map(line=>{const [name,lat,lon]=line.split("|").map(x=>x.trim());return{name:name||"?",lat:Number(lat)||0,lon:Number(lon)||0};});
      else if(vox&&field==="highlight_countries")v.highlight_countries=value.split(",").map(x=>x.trim()).filter(Boolean);
      else if(vox&&field==="route"){const parts=value.split("|").map(x=>Number(x.trim())-1).filter(n=>Number.isInteger(n)&&n>=0);v.route=parts.length===2?parts:[];}
      else if(field==="kind"&&vox&&["quote","chart","timeline","map"].includes(value)){
        s.visual=value==="quote"?{kind:"quote",text:s.intent,highlight:"",attribution:""}:value==="chart"?{kind:"chart",chart_type:"bar",title:"",unit:"",items:[{label:"A",value:0},{label:"B",value:0}]}
          :value==="timeline"?{kind:"timeline",title:"",events:[{when:"Then",label:"First"},{when:"Now",label:"Today"}]}:{kind:"map",title:"",places:[{name:"Hanoi",lat:21.03,lon:105.85}],highlight_countries:[],route:[]};
        s.needs_fact_review=true;renderFields();}
      else if(field==="kind"){s.visual=value==="activity"?{kind:"activity",activity_id:state.stage.activities[0]?.id??"",caption:""}:value==="photo"?{kind:"photo",asset:null,prompt:"",fit:"contain",important_regions:[]}:value==="diagram"?{kind:"diagram",template:"steps",title:"",nodes:[{id:"n1",label:"First step"},{id:"n2",label:"Next step"}],edges:[]}:{kind:"text_card",title:"Key idea",bullets:[]};s.needs_fact_review=true;renderFields();}
      else if(field==="asset"){v.asset=value===""?null:state.assets[Number(value)].asset;renderFields();}
      else if(field==="bullets")v.bullets=value.split("\n").filter(Boolean);
      else if(field==="nodes"){const unused=[...v.nodes],ids=new Set(v.nodes.map(n=>n.id));let next=1;
        // Keep a node's ID by label, not line position, so edges never reconnect to a neighbour.
        v.nodes=value.split("\n").filter(Boolean).map(line=>{const [label,...rest]=line.split("|"),text=label.trim(),match=unused.findIndex(n=>n.label.trim()===text);
          let id;if(match>=0)id=unused.splice(match,1)[0].id;else{while(ids.has(`node-${next}`))next++;id=`node-${next}`;ids.add(id);}
          return{id,label:text,detail:rest.join("|").trim()};});v.edges=(v.edges??[]).filter(edge=>v.nodes.some(n=>n.id===edge.source)&&v.nodes.some(n=>n.id===edge.target));}
      else if(field==="gestures")s.gestures=value.split("\n").filter(Boolean).map(line=>{const [id,index,gesture]=line.split("|").map(x=>x.trim());return{at:{line_id:id,token_index:Number(index)},gesture};});
      else if(["x","y","height"].includes(field)&&l)l.presenter[field]=Number(value);
      else if(field==="anchor"&&l){l.presenter.anchor=value;const x=state.geometry?.aspects?.[state.aspect]?.anchor_options?.[value];if(x!==undefined)l.presenter.x=x;renderFields();}
      else if(field==="transition"&&l){l.transition=value;if(value==="cut")l.motion_from=null;}
      else v[field]=value;
      changed();});
    container.addEventListener("change",async e=>{
      if(e.target.id==="solo-aspect"){await save().catch(fail);state.aspect=e.target.value;state.previewToken++;render();preview().catch(fail);}
      if(e.target.dataset.unlock){const s=state.segments[state.selected];state.unlock??={};state.unlock[s.id]??=[];const key=e.target.dataset.unlock;
        state.unlock[s.id]=state.unlock[s.id].filter(item=>item!==key);if(!e.target.checked)state.unlock[s.id].push(key);s.locks[key]=e.target.checked;changed();}
      if(e.target.id==="vox-picture-upload"&&e.target.files[0]&&!state.busy){state.busy=true;controls();try{const asset=await Api.uploadExplainerAsset(projectId,e.target.files[0]);state.assets=await Api.listExplainerAssets(projectId);
        const s=state.segments[state.selected];s.visual={kind:"photo",asset:asset.asset,prompt:s.visual.kind==="photo"?s.visual.prompt??"":"",caption:"",fit:"cover",important_regions:[]};s.needs_fact_review=true;changed();renderFields();await save();message("The picture is used for this segment.");}catch(error){fail(error);}finally{state.busy=false;controls();}}
      if(e.target.id==="vox-references"&&e.target.files.length&&!state.busy){state.busy=true;controls();try{for(const file of e.target.files)await Api.uploadExplainerAsset(projectId,file);state.assets=await Api.listExplainerAssets(projectId);render();message("Reference pictures added: the next proposal can use them.");}catch(error){fail(error);}finally{state.busy=false;controls();}}
      if(e.target.id==="solo-upload"&&e.target.files[0]&&!state.busy){state.busy=true;controls();try{const asset=await Api.uploadExplainerAsset(projectId,e.target.files[0]);state.assets=await Api.listExplainerAssets(projectId);state.segments[state.selected].visual.asset=asset.asset;changed();renderFields();await save();}catch(error){fail(error);}finally{state.busy=false;controls();}}
    });
    const before=e=>{if(state.dirty||state.busy||state.saving){e.preventDefault();e.returnValue="";}};
    const navigate=async e=>{const link=e.target.closest("a[href]");if(!link||(!state.dirty&&!state.busy&&!state.saving)||link.hasAttribute("download"))return;e.preventDefault();
      if(state.busy){message("Wait for the active operation, or cancel the proposal before leaving.",true);return;}
      if(await ConfirmDialog.ask("Save your plan before leaving?",{confirmLabel:"Save and leave"})){try{await save();if(!state.dirty&&!state.conflict)window.location.href=link.href;}catch(error){fail(error);}}};
    window.addEventListener("beforeunload",before);document.addEventListener("click",navigate,true);
    const destroy=()=>{state.disposed=true;clearTimeout(state.timer);state.previewToken++;state.preview?.destroy();window.removeEventListener("beforeunload",before);document.removeEventListener("click",navigate,true);};
    window.addEventListener("pagehide",destroy,{once:true});
    try {await reload();const active=await Api.getActiveAiJob(projectId,"propose_explainer");if(active)message(`A durable proposal is ${active.status}. Propose returns the existing job while it is active.`);}catch(error){fail(error);}
    return {destroy,save,hasUnsaved:()=>state.dirty||!!state.saving};
  }
  return {mount};
})();
