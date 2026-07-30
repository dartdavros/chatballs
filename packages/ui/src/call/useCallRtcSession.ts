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
  const preparingRef = useRef(false);
  const videoEnabledRef = useRef(options.videoEnabled ?? true);
  videoEnabledRef.current = options.videoEnabled ?? true;
  const onCallStateRef = useRef(options.onCallState);
  onCallStateRef.current = options.onCallState;

  const stop = useCallback(() => {
    clientRef.current?.dispose();
    clientRef.current = null;
    localRef.current?.getTracks().forEach((track) => track.stop());
    localRef.current = null;
    setLocalStream(null);
    setRemoteStream(null);
  }, []);

  const prepare = useCallback(async () => {
    if (localRef.current || preparingRef.current || !navigator.mediaDevices?.getUserMedia || typeof RTCPeerConnection === "undefined") {
      if (!navigator.mediaDevices?.getUserMedia || typeof RTCPeerConnection === "undefined") setMediaIssue("unsupported");
      return;
    }
    preparingRef.current = true;
    setPreparing(true);
    try {
      // Аудиозвонок: видео не запрашивается и не откатывается — это честный
      // аудио-режим. Видеозвонок: video+audio, при отказе камеры — audio-only.
      const constraints: MediaStreamConstraints = videoEnabledRef.current
        ? { audio: true, video: true }
        : { audio: true, video: false };
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        setMediaIssue("none");
        if (!videoEnabledRef.current) setCamOn(false);
      } catch {
        if (videoEnabledRef.current) {
          stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
          setCamOn(false);
          setMediaIssue("video");
        } else {
          throw new Error("audio devices unavailable");
        }
      }
      localRef.current = stream;
      setLocalStream(stream);
    } catch {
      setCamOn(false);
      setMicOn(false);
      setMediaIssue("devices");
    } finally {
      preparingRef.current = false;
      setPreparing(false);
    }
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

  const start = useCallback(() => {
    if (!options.accessToken || clientRef.current) return false;
    if (mediaIssue === "devices") setMediaIssue("none");
    const client = new CallRtcClient({
      accessToken: options.accessToken,
      side: options.side,
      iceServers: options.iceServers,
      localStream: localRef.current,
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
  }, [mediaIssue, options.accessToken, options.iceServers, options.side, stop]);

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
    await prepare();
    return start();
  }, [prepare, start, stop]);

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
