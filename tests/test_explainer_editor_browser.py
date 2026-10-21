"""Real browser checks for serialized/trailing saves and visible conflict recovery."""
import asyncio

import pytest
from playwright.async_api import async_playwright, expect

from tests.conftest import live_server


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    with live_server(tmp_path_factory, "explainer-editor") as url:
        yield url


@pytest.fixture
async def editor(base_url):
    async with async_playwright() as driver:
        browser = await driver.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        await page.goto(base_url + "/characters")
        await page.add_script_tag(url=base_url + "/static/js/explainer_editor.js")
        await page.evaluate("""async () => {
          const segment={id:'one',intent:'Original purpose',line_ids:['line'],start:{line_id:'line',token_index:0},end:{line_id:'line',token_index:3},
            visual:{kind:'text_card',title:'Small steps',bullets:['Begin today']},gestures:[],layouts:{},locks:{},needs_fact_review:true,source_notes:''};
          window.saved=[];window.inflight=0;window.maxInflight=0;window.releaseSave=null;window.hold=false;window.conflict=false;
          window.serverView={plan:{revision:1,status:'draft',segments:[segment],aspects:['16:9','9:16']},current_source_fingerprint:'fingerprint',issues:[]};
          Api.getExplainerPlan=async()=>structuredClone(window.serverView);Api.listExplainerAssets=async()=>[];Api.getActiveAiJob=async()=>null;
          Api.saveExplainerPlan=async(pid,body)=>{
            window.inflight++;window.maxInflight=Math.max(window.maxInflight,window.inflight);window.saved.push(structuredClone(body));
            if(window.hold)await new Promise(resolve=>window.releaseSave=resolve);
            window.inflight--;if(window.conflict)throw Object.assign(new Error('Newer revision exists'),{status:409});
            window.serverView.plan={...window.serverView.plan,revision:body.expected_revision+1,segments:body.segments};return structuredClone(window.serverView);
          };
          const node=document.createElement('div');node.id='editor-fixture';document.body.replaceChildren(node);
          window.editor=await ExplainerEditor.mount(node,'project-fixture');
        }""")
        yield page
        await page.evaluate("window.editor.destroy()")
        await browser.close()


async def test_trailing_autosave_preserves_edits_during_inflight_request(editor):
    await editor.evaluate("window.hold=true")
    purpose = editor.locator('[data-field="intent"]')
    await purpose.fill("First edit")
    await editor.wait_for_function("window.saved.length===1")
    await purpose.fill("Latest edit while saving")
    await editor.evaluate("window.hold=false;window.releaseSave()")
    await editor.wait_for_function("window.saved.length===2 && window.inflight===0")
    assert await editor.evaluate("window.maxInflight") == 1
    assert await editor.evaluate("window.saved[1].expected_revision") == 2
    await expect(purpose).to_have_value("Latest edit while saving")
    await editor.locator('[data-action="save"]').click()
    assert await editor.evaluate("window.saved.length") == 2


async def test_conflict_keeps_local_draft_and_stops_autosave(editor):
    await editor.evaluate("window.conflict=true")
    purpose = editor.locator('[data-field="intent"]')
    await purpose.fill("Keep my local draft")
    await expect(editor.locator("#solo-error")).to_contain_text("draft is retained")
    await expect(purpose).to_have_value("Keep my local draft")
    await expect(editor.locator('[data-action="approve"]')).to_be_disabled()
    await purpose.fill("Still retained after conflict")
    await asyncio.sleep(.6)
    assert await editor.evaluate("window.saved.length") == 1


async def test_operation_flush_locks_double_submit_and_editing(editor):
    await editor.evaluate("window.hold=true")
    purpose = editor.locator('[data-field="intent"]')
    await purpose.fill("Save this exactly once")
    await editor.locator('[data-action="save"]').click()
    await expect(purpose).to_be_disabled()
    await expect(editor.locator('[data-action="arrange"]')).to_be_disabled()
    await editor.evaluate("window.hold=false;window.releaseSave()")
    await expect(purpose).to_be_enabled()
    assert await editor.evaluate("window.saved.length") == 1


async def test_diagram_node_ids_follow_labels_so_edges_never_reconnect(editor):
    await editor.evaluate("""async () => {
      window.editor.destroy();
      const segment=window.serverView.plan.segments[0];
      segment.visual={kind:'diagram',template:'steps',title:'Habit loop',nodes:[{id:'a',label:'Cue'},{id:'b',label:'Routine'},{id:'c',label:'Reward'}],
        edges:[{source:'b',target:'c'}]};
      const node=document.createElement('div');document.body.replaceChildren(node);
      window.editor=await ExplainerEditor.mount(node,'project-fixture');
    }""")
    await editor.locator('[data-field="nodes"]').fill("Routine\nReward\nCraving")
    await editor.wait_for_function("window.saved.length===1")
    visual = await editor.evaluate("window.saved[0].segments[0].visual")
    assert [(n["id"], n["label"]) for n in visual["nodes"]] == [("b", "Routine"), ("c", "Reward"), ("node-1", "Craving")]
    assert visual["edges"] == [{"source": "b", "target": "c"}]


async def test_scene_and_activity_pickers_save_the_stage_choice(editor):
    # Phase 55 (ENH-037): the owner can change the AI's scene and activity picture per segment.
    await editor.evaluate("""async () => {
      window.editor.destroy();
      Api.getExplainerStageChoices=async()=>({scenes:[{id:'builtin-office',name:'Office',category:'work'},{id:'builtin-park',name:'Park',category:'city'}],
        activities:[{id:'act-drive',activity:'driving',presenter_own:true}]});
      const node=document.createElement('div');document.body.replaceChildren(node);
      window.editor=await ExplainerEditor.mount(node,'project-fixture');
    }""")
    await editor.locator('[data-field="scene"]').select_option("builtin-park")
    await editor.locator('[data-field="kind"]').select_option("activity")
    await expect(editor.locator('[data-field="activity"]')).to_have_value("act-drive")
    await editor.wait_for_function("window.saved.length>=1 && window.saved.at(-1).segments[0].visual.kind==='activity'")
    segment = await editor.evaluate("window.saved.at(-1).segments[0]")
    assert segment["scene"] == {"scene_id": "builtin-park"}
    assert segment["visual"] == {"kind": "activity", "activity_id": "act-drive", "caption": ""}
