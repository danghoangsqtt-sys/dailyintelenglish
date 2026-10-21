"""Phase 59 (ENH-041): the VOX card on Step 1 and the VOX editor on Step 5 (pictures from an outside AI or your own)."""
import pytest
from playwright.async_api import async_playwright, expect

from tests.conftest import live_server


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    with live_server(tmp_path_factory, "vox-browser") as url:
        yield url


@pytest.fixture
async def page():
    async with async_playwright() as driver:
        browser = await driver.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        yield page
        await browser.close()


async def result(response):
    assert response.status == 200, await response.text()
    return (await response.json())["data"]


async def test_the_vox_card_makes_a_vox_project_with_a_narrator_voice(page, base_url):
    profile = await result(await page.request.post(base_url + "/api/visuals/profiles", data={
        "name": "Voice Narrator", "gender": "female", "accent": "american", "appearance": "dark hair", "outfit": "green coat",
    }))
    await page.goto(base_url + "/step1")
    await page.locator(".type-card[data-mode='vox']").click()
    await expect(page.locator(".type-card[data-mode='vox']")).to_have_attribute("aria-checked", "true")
    await expect(page.locator(".type-card[data-mode='solo_explainer']")).to_have_attribute("aria-checked", "false")
    await expect(page.locator("#presentation-mode")).to_have_value("solo_explainer")
    await expect(page.locator("#subject-cards")).to_be_visible()
    await expect(page.locator(".speaker-slot").first).to_have_text("Narrator (voice only)")
    await page.locator("#name").fill("A VOX video")
    await page.locator("#topic").fill("Why coffee wakes us up")
    await page.locator("button[data-choose='0']").click()
    await page.locator(f".cs-card[data-id='{profile['id']}']").click()
    await expect(page.locator("#cs-preview, .cs-preview").first).to_contain_text("only the voice is used")
    await page.locator("[data-cs='choose']").click()
    await page.locator("[data-cs='close']").click()
    await page.locator("#submit-btn").click()
    await page.wait_for_url("**/step2?**")
    projects = await result(await page.request.get(base_url + "/api/projects"))
    created = next(item for item in projects if item["name"] == "A VOX video")
    stored = await result(await page.request.get(base_url + f"/api/projects/{created['id']}"))
    assert (stored["presentation_mode"], stored["explainer_style"]) == ("solo_explainer", "vox")


async def test_the_vox_editor_offers_vox_kinds_a_picture_prompt_and_my_picture(page, base_url):
    await page.goto(base_url + "/characters")
    await page.add_script_tag(url=base_url + "/static/js/explainer_editor.js")
    await page.evaluate("""async () => {
      const segment={id:'one',intent:'Coffee hides tiredness',line_ids:['line'],start:{line_id:'line',token_index:0},end:{line_id:'line',token_index:3},
        visual:{kind:'quote',text:'Coffee hides tiredness',highlight:'tiredness',attribution:''},scene:null,gestures:[],layouts:{},locks:{},needs_fact_review:true,source_notes:''};
      window.saved=[];window.uploads=0;
      window.serverView={plan:{revision:1,status:'draft',segments:[segment],aspects:['16:9','9:16']},current_source_fingerprint:'f',issues:[]};
      Api.getExplainerPlan=async()=>structuredClone(window.serverView);Api.listExplainerAssets=async()=>window.uploads?[{asset:{asset_id:'mine',version:1},filename:'mine.png',preview_url:''}]:[];
      Api.getActiveAiJob=async()=>null;Api.getExplainerStageChoices=async()=>({scenes:[{id:'cafe',name:'Cafe',category:'city'}],activities:[]});
      Api.uploadExplainerAsset=async()=>{window.uploads++;return {asset:{asset_id:'mine',version:1}};};
      Api.saveExplainerPlan=async(pid,body)=>{window.saved.push(structuredClone(body));window.serverView.plan={...window.serverView.plan,revision:body.expected_revision+1,segments:body.segments};return structuredClone(window.serverView);};
      const node=document.createElement('div');document.body.replaceChildren(node);
      window.editor=await ExplainerEditor.mount(node,'project-fixture',{style:'vox',topic:'Why coffee wakes us up'});
    }""")
    kinds = await page.locator('[data-field="kind"] option').all_text_contents()
    assert kinds == ["quote", "text_card", "diagram", "chart", "timeline", "map", "activity", "photo"]
    await expect(page.locator('[data-action="arrange"]')).to_have_count(0)  # nobody to place
    await expect(page.locator('[data-field="anchor"]')).to_have_count(0)
    await expect(page.locator('[data-field="gestures"]')).to_have_count(0)
    prompt = await page.locator("#vox-picture-prompt").input_value()
    assert "Coffee hides tiredness" in prompt and "Why coffee wakes us up" in prompt and "No text" in prompt
    await page.locator('[data-field="kind"]').select_option("chart")
    await page.locator('[data-field="items"]').fill("Fail | 45\nLast | 55")
    await page.wait_for_function("window.saved.length > 0 && window.saved.at(-1).segments[0].visual.kind === 'chart'")
    assert await page.evaluate("window.saved.at(-1).segments[0].visual.items") == [{"label": "Fail", "value": 45}, {"label": "Last", "value": 55}]
    await page.locator("#vox-picture-upload").set_input_files({"name": "mine.png", "mimeType": "image/png", "buffer": b"png"})
    await page.wait_for_function("window.saved.at(-1).segments[0].visual.kind === 'photo'")
    assert await page.evaluate("window.saved.at(-1).segments[0].visual.asset") == {"asset_id": "mine", "version": 1}
    await page.evaluate("window.editor.destroy()")
