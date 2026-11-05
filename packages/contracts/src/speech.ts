export type MicrophoneMode = "off" | "voice_message" | "dictation";

export type WebSpeechCapabilities = {
  microphoneMode: MicrophoneMode;
  maxRecordingBytes: number;
  maxDictationSeconds: number;
  available: boolean;
};

export type SpeechCapabilities = {
  stt: boolean;
  default_model: string;
  models: string[];
  languages: string[];
  formats: string[];
  max_bytes: number;
  max_seconds: number;
};
