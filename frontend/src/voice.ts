// Microphone capture as 16 kHz mono WAV (what the local whisper.cpp service expects) and on-device read-aloud.
const RATE=16000;
export const MAX_SECONDS=300;

export function encodeWav(samples:Float32Array,rate=RATE):Blob{
 const view=new DataView(new ArrayBuffer(44+samples.length*2));
 const text=(offset:number,value:string)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};
 text(0,'RIFF');view.setUint32(4,36+samples.length*2,true);text(8,'WAVE');text(12,'fmt ');
 view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);
 view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,'data');view.setUint32(40,samples.length*2,true);
 samples.forEach((s,i)=>view.setInt16(44+i*2,Math.max(-1,Math.min(1,s))*0x7fff,true));
 return new Blob([view],{type:'audio/wav'});
}

function resample(samples:Float32Array,from:number):Float32Array{
 if(from===RATE)return samples;
 const out=new Float32Array(Math.floor(samples.length*RATE/from)),step=from/RATE;
 for(let i=0;i<out.length;i++){const x=i*step,j=Math.floor(x),f=x-j;out[i]=samples[j]*(1-f)+(samples[j+1]??samples[j])*f;}
 return out;
}

export type Recording={stop:()=>Promise<Blob>;cancel:()=>void};
// Raw PCM capture: the browser records at 16 kHz where it can, so no encode/decode step is needed.
export async function record(onLimit:()=>void):Promise<Recording>{
 const stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true}});
 let context:AudioContext|undefined;
 try{
  let source:MediaStreamAudioSourceNode;
  try{context=new AudioContext({sampleRate:RATE});source=context.createMediaStreamSource(stream);}
  catch{context?.close();context=new AudioContext();source=context.createMediaStreamSource(stream);}
  const ctx=context,limit=MAX_SECONDS*ctx.sampleRate,parts:Float32Array[]=[];let total=0,done=false;
  await ctx.audioWorklet.addModule('/recorder-worklet.js');
  const node=new AudioWorkletNode(ctx,'foxory-recorder');
  node.port.onmessage=e=>{if(done)return;const block=(e.data as Float32Array).subarray(0,limit-total);parts.push(block);total+=block.length;if(total>=limit){done=true;onLimit();}};
  // Connected to the output so every browser runs it; the processor writes silence.
  source.connect(node);node.connect(ctx.destination);
  const release=()=>{done=true;source.disconnect();node.disconnect();stream.getTracks().forEach(t=>t.stop());ctx.close();};
  return {
   stop:async()=>{release();const all=new Float32Array(total);let at=0;for(const p of parts){all.set(p,at);at+=p.length;}return encodeWav(resample(all,ctx.sampleRate).subarray(0,MAX_SECONDS*RATE));},
   cancel:release,
  };
 }catch(e){stream.getTracks().forEach(t=>t.stop());context?.close();throw e;}
}

// Read-aloud uses the browser's built-in voices, which run on this device.
export const canSpeak=typeof window!=='undefined'&&'speechSynthesis' in window;
export function plainText(markdown:string){
 return markdown.replace(/```[\s\S]*?```/g,' Code omitted. ').replace(/`([^`]*)`/g,'$1').replace(/!\[[^\]]*\]\([^)]*\)/g,'').replace(/\[([^\]]*)\]\([^)]*\)/g,'$1').replace(/^[#>\-*+\s]+/gm,'').replace(/[*_~|]/g,'').replace(/\s+/g,' ').trim();
}
export function speak(markdown:string,onEnd?:()=>void){
 if(!canSpeak)return;
 window.speechSynthesis.cancel();
 const utterance=new SpeechSynthesisUtterance(plainText(markdown));
 // Let the voice follow the reply's script, e.g. Arabic replies use an Arabic voice when installed.
 utterance.lang=/[؀-ۿ]/.test(markdown)?'ar':document.documentElement.lang||navigator.language;
 utterance.onend=()=>onEnd?.();utterance.onerror=()=>onEnd?.();
 window.speechSynthesis.speak(utterance);
}
export function stopSpeaking(){if(canSpeak)window.speechSynthesis.cancel();}
