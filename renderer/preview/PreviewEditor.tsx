import React, {useCallback, useEffect, useRef, useState} from "react";
import {Player, type PlayerRef} from "@remotion/player";
import {Episode} from "../src/Episode";
import type {EpisodeInputProps} from "../src/types";

/** Keep transport outside the picture so controls cannot cover scaled-down captions. */
export function PreviewEditor({props,onReady}:{props:EpisodeInputProps;onReady?:(player:PlayerRef|null)=>void}) {
  const player=useRef<PlayerRef>(null),[frame,setFrame]=useState(0),[playing,setPlaying]=useState(false);
  const duration=props.introSec+(props.durationSeconds ?? props.lines.at(-1)?.endSec ?? 1)+props.outroSec;
  const frames=Math.max(1,Math.ceil(duration*props.fps));
  const attach=useCallback((value:PlayerRef|null)=>{player.current=value;onReady?.(value);},[onReady]);
  useEffect(()=>{
    const current=player.current;if(!current)return;
    const update=(event:{detail:{frame:number}})=>setFrame(event.detail.frame);
    const play=()=>setPlaying(true),pause=()=>setPlaying(false);
    current.addEventListener("frameupdate",update);current.addEventListener("play",play);current.addEventListener("pause",pause);
    return ()=>{current.removeEventListener("frameupdate",update);current.removeEventListener("play",play);current.removeEventListener("pause",pause);};
  },[props]);
  return <div style={{width:"100%",maxWidth:`calc(70vh * ${props.width/props.height})`}}>
    <Player ref={attach} component={Episode} inputProps={props} compositionWidth={props.width} compositionHeight={props.height}
      durationInFrames={frames} fps={props.fps} controls={false} acknowledgeRemotionLicense style={{width:"100%",aspectRatio:`${props.width}/${props.height}`}} />
    <div className="solo-player-transport">
      <button type="button" className="btn btn-ghost" onClick={()=>{if(playing)player.current?.pause();else player.current?.play();}}>{playing?"Pause":"Play"}</button>
      <input aria-label="Preview frame" type="range" min={0} max={frames-1} value={Math.min(frame,frames-1)}
        onChange={event=>{player.current?.pause();player.current?.seekTo(Number(event.target.value));}} />
      <span aria-live="off">{(frame/props.fps).toFixed(1)} / {duration.toFixed(1)} s</span>
    </div>
  </div>;
}
