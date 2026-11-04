import {describe,it,expect} from "vitest";
import {PRESENTER_SWAY,presenterBody,presenterFade,presenterPose,presenterState,segmentPhrases} from "./presenterTimeline";
import {stagePush} from "./SoloStage";
import type {SoloPayload,Gesture} from "./soloTypes";
import type {EpisodeLine} from "./types";

const gestures:Gesture[]=["calm","talk","point-left","point-right","emphasize","count-1","count-2","count-3","think","wave"];
const pictures=Object.fromEntries(["calm__closed","calm__open","blink",...gestures.filter(g=>g!=="calm").flatMap(g=>[`gesture-${g}`,`gesture-${g}__open`])].map(k=>[k,k]));
function payload(gesture:Gesture):SoloPayload{return {plan:{project_id:"p",revision:1,status:"approved",source_fingerprint:"a",aspects:["16:9"],segments:[{id:"idea"}]},timeline:[{id:"idea",start_sec:0,end_sec:10,gestures:[{gesture,at_sec:2}]}],pictures} as SoloPayload;}
const lines:EpisodeLine[]=[{startSec:1,endSec:5,speaker:"Presenter",speakerId:"s",text:"One real word",words:[{text:"real",startSec:2,endSec:2.8}]}];
describe("Solo deterministic pictures",()=>{
  it.each(gestures)("selects %s in both speaking mouth states without dropping the figure",gesture=>{
    const data=payload(gesture),closed=gesture==="calm"?"calm__closed":`gesture-${gesture}`;
    const open=gesture==="calm"?"calm__open":`${closed}__open`;
    const shown=new Set(Array.from({length:24},(_,i)=>presenterState(data,lines,2+i/30,30).picture));
    expect(shown.has(closed)).toBe(true);expect(shown.has(open)).toBe(true);
  });
  it("seeking backwards returns the same picture and blink happens only in silence",()=>{
    const data=payload("wave"),before=presenterState(data,lines,2.4,30);
    presenterState(data,lines,9,30);expect(presenterState(data,lines,2.4,30)).toEqual(before);
    expect(presenterState(data,[],4.1,30).picture).toBe("blink");
    expect(presenterState(data,lines,2.1,30).picture).not.toBe("blink");
  });
  it("refuses a missing pose instead of briefly disappearing",()=>{
    const data=payload("wave");data.pictures={...data.pictures};delete data.pictures["gesture-wave__open"];
    expect(()=>presenterState(data,lines,2.1,30)).toThrow("pinned front pack");
  });
});

describe("Phase 61 lively presenter (ENH-043)",()=>{
  const speech:EpisodeLine[]=[{startSec:0,endSec:9,speaker:"Presenter",speakerId:"s",text:"many words",
    words:Array.from({length:12},(_,i)=>({text:i%3?"word":"wonderful",startSec:.3+i*.7+(i>5?.6:0),endSec:.8+i*.7+(i>5?.6:0)}))}];
  const quiet={...payload("wave"),timeline:[{id:"idea",start_sec:0,end_sec:10,gestures:[]}]} as SoloPayload;
  it("changes gesture per phrase between planned cues, with rests",()=>{
    const poses=new Set(Array.from({length:270},(_,i)=>presenterPose(presenterState(quiet,speech,i/30,30).picture)));
    expect(poses.has("gesture-talk")).toBe(true);
    expect(poses.has("calm")).toBe(true);
    expect(segmentPhrases(speech,0,10).length).toBeGreaterThanOrEqual(2);
  });
  it("keeps the bob and sway inside the layout proof margin with the breathing",()=>{
    for(let i=0;i<600;i++){const body=presenterBody(speech,i/60);
      expect(Math.abs(body.x)).toBeLessThanOrEqual(PRESENTER_SWAY.x);expect(Math.abs(body.y)+.001).toBeLessThan(.006);}
    const onset=speech[0].words[0].startSec;
    expect(presenterBody(speech,onset+.14).y).toBeLessThan(presenterBody(speech,onset-.01).y);
  });
  it("cross-fades only a pose change",()=>{
    let found=false;
    for(let frame=1;frame<270;frame++){
      const now=presenterState(quiet,speech,frame/30,30).picture,before=presenterState(quiet,speech,(frame-1)/30,30).picture;
      const fade=presenterFade(quiet,speech,frame/30,30);
      if(presenterPose(now)!==presenterPose(before)){expect(fade?.picture).toBe(before);found=true;}
      if(fade) expect(fade.opacity).toBeLessThan(1);
    }
    expect(found).toBe(true);
    expect(stagePush(0,0,10)).toBe(1);expect(stagePush(5,0,10)).toBeCloseTo(1.05);expect(stagePush(10,0,10)).toBe(1);
  });
});
