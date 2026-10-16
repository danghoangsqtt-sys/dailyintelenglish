import {describe,it,expect} from "vitest";
import {presenterState} from "./presenterTimeline";
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
