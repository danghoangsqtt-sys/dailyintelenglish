import React, {useMemo} from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { Presenter } from "./Presenter";
import { ExplainerVisual } from "./ExplainerVisual";
import { CaptionBand } from "./CaptionBand";
import { presenterState } from "./presenterTimeline";
import type { EpisodeInputProps } from "./types";
import type { SoloSegment } from "./soloTypes";

export function SoloScene(props: EpisodeInputProps) {
  const frame = useCurrentFrame(), {fps, width, height} = useVideoConfig();
  const payload = props.solo;
  if (!payload) throw new Error("A Solo scene needs its reviewed payload");
  const time = frame/fps, aspect = props.layout === "vertical" ? "9:16" : "16:9";
  const {segmentIndex} = presenterState(payload,props.lines,time,fps);
  const segment = payload.plan.segments[segmentIndex], geometry = payload.geometry.aspects[aspect];
  const line = props.lines.find(item=>time>=item.startSec && time<item.endSec);
  const photo = segment.visual.kind === "photo" && segment.visual.asset ? payload.photos[`${segment.visual.asset.asset_id}:${segment.visual.asset.version}`] : undefined;
  const visual = {...segment,photoUrl:photo} as SoloSegment;
  const caption = geometry.caption, header = geometry.header;
  const span=payload.timeline[segmentIndex];
  const cues=useMemo(()=>props.lines.flatMap(item=>item.words).filter(word=>word.startSec>=span.start_sec && word.startSec<span.end_sec),[props.lines,span]);
  const progress=cues.length?cues.filter(word=>word.startSec<=time).length/cues.length:1;
  const hook=props.hook && time>=(props.hookAtSec??0) && time<(props.hookAtSec??0)+3;
  return <AbsoluteFill data-solo-scene="true" style={{background:"radial-gradient(ellipse at 50% 30%,#1B4939,#071D18 72%)",fontFamily:"Arial,sans-serif",overflow:"hidden"}}>
    <div style={{position:"absolute",left:header.x*width,top:header.y*height,width:header.width*width,height:header.height*height,
      color:"#D9E7CE",fontSize:aspect==="9:16"?26:20,display:"flex",justifyContent:"space-between",alignItems:"center",overflow:"hidden"}}>
      <span style={{whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{hook?props.hook:"DAILY BEYOND ENGLISH"}</span><span>{props.cefrLevel}</span>
    </div>
    <ExplainerVisual segment={visual} proof={geometry.segments[segmentIndex]} aspect={aspect} progress={progress}/>
    <Presenter payload={payload} lines={props.lines} time={time} aspect={aspect}/>
    {line ? <div data-solo-caption="true" style={{position:"absolute",left:caption.x*width,top:caption.y*height,width:caption.width*width,height:caption.height*height}}>
      <CaptionBand line={line} currentTimeSec={time} captionStyle={props.captionStyle} layout={props.layout}
        protectedPhrases={[...(props.learning?.idioms ?? []).map(item=>item.phrase),...(props.learning?.vocab ?? []).map(item=>item.word)]} stationary />
    </div> : null}
  </AbsoluteFill>;
}
