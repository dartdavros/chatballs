import { CallRtcClient, type CallSide, type PublicCallState, type RtcConnectionPhase } from "@edevs/shared";
import { useCallback, useEffect, useRef, useState } from "react";

export type CallMediaIssue = "none" | "video" | "devices" | "unsupported";

type Options = {
  resetKey: string;
  previewEnabled: boolean;
  accessToken: string;
  side: CallSide;
  iceServers: RTCIceServer[];
  videoEnabled?: boolean;
  onCallState: (call: PublicCallState) => void;
};

const TERMINAL = new Set(["DECLINED", "CANCELLED", "MISSED", "ENDED", "FAILED", "EXPIRED"]);

export function useCallRtcSession(options: Options) {
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const [micOn, setMicOn] = useState(true);
  const [camOn, setCamOn] = useState(true);
  const [remoteMicOn, setRemoteMicOn] = useState(true);
  const [remoteCamOn, setRemoteCamOn] = useState(true);
  const [mediaIssue, setMediaIssue] = useState<CallMediaIssue>("none");
  const [connectionPhase, setConnectionPhase] = useState<RtcConnectionPhase | "idle">("idle");
  const [preparing, setPreparing] = useState(false);
  const localRef = useRef<MediaStream | null>(null);
  const clientRef = useRef<CallRtcClient | null>(null);
  const preparePromiseRef = useRef<Promise<MediaStream | null> | null>(null);
  const startPromiseRef = useRef<Promise<boolean> | null>(null);
  const generationRef = useRef(0);
  const videoEnabledRef = useRef(options.videoEnabled ?? true);
  videoEnabledRef.current = options.videoEnabled ?? true;
  const onCallStateRef = useRef(options.onCallState);
  onCallStateRef.current = options.onCallState;

  const stop = useCallback(() => {
    generationRef.current += 1;
    clientRef.current?.dispose();
    clientRef.current = null;
    localRef.current?.getTracks().forEach((track) => track.stop());
    localRef.current = null;
    preparePromiseRef.current = null;
    startPromiseRef.current = null;
    setLocalStream(null);
    setRemoteStream(null);
    setPreparing(false);
  }, []);

  const prepare = useCallback((): Promise<MediaStream | null> => {
    if (localRef.current) return Promise.resolve(localRef.current);
    if (!navigator.mediaDevices?.getUserMedia || typeof RTCPeerConnection === "undefined") {
      setMediaIssue("unsupported");
      return Promise.resolve(null);
    }
    if (preparePromiseRef.current) return preparePromiseRef.current;

    const generation = generationRef.current;
    const pending = (async () => {
      setPreparing(true);
      try {
        // Аудиозвонок запрашивает только микрофон. Видеозвонок сначала запрашивает
        // camera+microphone и честно откатывается в audio-only при проблеме камеры.
        const constraints: MediaStreamConstraints = videoEnabledRef.current
          ? { audio: true, video: true }
          : { audio: true, video: false };
        let stream: MediaStream;
        try {
          stream = await navigator.mediaDevices.getUserMedia(constraints);
          setMediaIssue("none");
          if (!videoEnabledRef.current) setCamOn(false);
        } catch {
          if (!videoEnabledRef.current) throw new Error("audio devices unavailable");
          stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
          setCamOn(false);
          setMediaIssue("video");
        }
        if (generation !== generationRef.current) {
          stream.getTracks().forEach((track) => track.stop());
          return null;
        }
        localRef.current = stream;
        setLocalStream(stream);
        setMicOn(stream.getAudioTracks().some((track) => track.enabled));
        return stream;
      } catch {
        setCamOn(false);
        setMicOn(false);
        setMediaIssue("devices");
        return null;
      }
    })();
    preparePromiseRef.current = pending;
    void pending.finally(() => {
      if (preparePromiseRef.current === pending) {
        preparePromiseRef.current = null;
        setPreparing(false);
      }
    });
    return pending;
  }, []);

  useEffect(() => {
    stop();
    setMicOn(true);
    setCamOn(videoEnabledRef.current);
    setRemoteMicOn(true);
    setRemoteCamOn(true);
    setMediaIssue("none");
    setConnectionPhase("idle");
  }, [options.resetKey, stop]);

  useEffect(() => {
    if (options.previewEnabled) void prepare();
  }, [options.previewEnabled, prepare]);

  useEffect(() => stop, [stop]);

  const start = useCallback((): Promise<boolean> => {
    if (clientRef.current) return Promise.resolve(true);
    if (!options.accessToken) return Promise.resolve(false);
    if (startPromiseRef.current) return startPromiseRef.current;

    const generation = generationRef.current;
    let pending: Promise<boolean>;
    pending = (async () => {
      const stream = localRef.current ?? await prepare();
      if (generation !== generationRef.current || !stream || clientRef.current) return Boolean(clientRef.current);
      const client = new CallRtcClient({
        accessToken: options.accessToken,
        side: options.side,
        iceServers: options.iceServers,
        localStream: stream,
        handlers: {
          onCallState: (call) => {
            onCallStateRef.current(call);
            if (TERMINAL.has(call.status)) queueMicrotask(stop);
          },
          onRemoteStream: setRemoteStream,
          onRemoteMedia: ({ mic, cam }) => {
            setRemoteMicOn(mic);
            setRemoteCamOn(cam);
          },
          onConnection: setConnectionPhase,
          onClosed: stop,
        },
      });
      clientRef.current = client;
      setConnectionPhase("connecting");
      client.start();
      return true;
    })().finally(() => {
      if (startPromiseRef.current === pending) startPromiseRef.current = null;
    });
    startPromiseRef.current = pending;
    return pending;
  }, [options.accessToken, options.iceServers, options.side, prepare, stop]);

  const toggleMic = useCallback(() => {
    setMicOn((current) => {
      const next = !current;
      clientRef.current?.setMediaState(next, camOn);
      localRef.current?.getAudioTracks().forEach((track) => { track.enabled = next; });
      return next;
    });
  }, [camOn]);

  const toggleCam = useCallback(() => {
    setCamOn((current) => {
      const next = !current;
      clientRef.current?.setMediaState(micOn, next);
      localRef.current?.getVideoTracks().forEach((track) => { track.enabled = next; });
      return next;
    });
  }, [micOn]);

  const end = useCallback(() => clientRef.current?.end(), []);
  const restart = useCallback(async () => {
    stop();
    setConnectionPhase("connecting");
    return start();
  }, [start, stop]);

  return {
    localStream,
    remoteStream,
    micOn,
    camOn,
    remoteMicOn,
    remoteCamOn,
    mediaIssue,
    connectionPhase,
    preparing,
    prepare,
    start,
    restart,
    end,
    stop,
    toggleMic,
    toggleCam,
  };
}
