// Copies microphone samples to the page; FOXORY encodes them as 16 kHz WAV for local transcription.
class FoxoryRecorder extends AudioWorkletProcessor{
 process(inputs){const channel=inputs[0]&&inputs[0][0];if(channel)this.port.postMessage(channel.slice(0));return true;}
}
registerProcessor('foxory-recorder',FoxoryRecorder);
