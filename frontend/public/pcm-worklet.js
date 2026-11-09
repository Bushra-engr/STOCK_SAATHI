class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.position = 0;
    this.ratio = sampleRate / 16000;
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel) return true;

    // The browser may ignore AudioContext's requested rate and provide 48 kHz.
    // Gnani's streaming endpoint expects 16 kHz, so resample before PCM16 encoding.
    const output = [];
    while (this.position < channel.length) {
      const index = Math.floor(this.position);
      const fraction = this.position - index;
      const first = channel[index];
      const second = channel[Math.min(index + 1, channel.length - 1)];
      output.push(first + (second - first) * fraction);
      this.position += this.ratio;
    }
    this.position -= channel.length;

    const pcm = new Int16Array(output.length);
    for (let i = 0; i < output.length; i += 1) {
      const value = Math.max(-1, Math.min(1, output[i]));
      pcm[i] = value < 0 ? value * 32768 : value * 32767;
    }
    this.port.postMessage(pcm.buffer, [pcm.buffer]);
    return true;
  }
}
registerProcessor('pcm-processor', PCMProcessor);
