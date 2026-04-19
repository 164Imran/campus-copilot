import { useState, useRef, useEffect } from 'react';

export default function TUMVoice() {
  const [isRecording, setIsRecording] = useState(false);
  const [sttText, setSttText] = useState({ final: "", partial: "" });
  const [agentText, setAgentText] = useState("...");

  const socketRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const fullTranscriptRef = useRef<string>("");
  const audioQueueRef = useRef<Blob[]>([]);
  const isPlayingRef = useRef<boolean>(false);

  const sttContainerRef = useRef<HTMLDivElement>(null);
  const agentContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sttContainerRef.current) {
      sttContainerRef.current.scrollTop = sttContainerRef.current.scrollHeight;
    }
  }, [sttText]);

  useEffect(() => {
    if (agentContainerRef.current) {
      agentContainerRef.current.scrollTop = agentContainerRef.current.scrollHeight;
    }
  }, [agentText]);

  const playNextAudio = () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }
    isPlayingRef.current = true;
    const audioBlob = audioQueueRef.current.shift()!;
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    audio.onended = () => {
      playNextAudio();
    };
    audio.play();
  };

  const startRecording = async () => {
    fullTranscriptRef.current = "";
    setSttText({ final: "", partial: "" });
    setAgentText("...");

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.close();
    }

    const socket = new WebSocket('ws://localhost:8000/ws/stream');
    socket.binaryType = "blob";
    socketRef.current = socket;

    socket.onopen = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0 && socket.readyState === 1) {
            socket.send(event.data);
          }
        };

        mediaRecorder.start(250);
        setIsRecording(true);
      } catch (error) {
        console.error("Erreur d'accès au micro", error);
      }
    };

    socket.onmessage = async (event) => {
      // CAS 1 : RÉCEPTION AUDIO (Binaire)
      if (event.data instanceof Blob) {
        console.log("🔊 Audio reçu d'ElevenLabs");
        audioQueueRef.current.push(event.data);
        if (!isPlayingRef.current) {
          playNextAudio();
        }
        return;
      }

      // CAS 2 : RÉCEPTION TEXTE (JSON)
      try {
        const data = JSON.parse(event.data);

        // Transcription en direct (STT)
        if (data.type === "stt") {
          if (data.is_final) {
            fullTranscriptRef.current += data.text + " ";
            setSttText({ final: fullTranscriptRef.current, partial: "" });
          } else {
            setSttText({ final: fullTranscriptRef.current, partial: data.text });
          }
        }
        // Réponse de l'Agent (Bedrock)
        else if (data.type === "agent") {
          setAgentText("🤖 " + data.text);
        }
      } catch (e) {
        console.error("Erreur de parsing JSON", e);
      }
    };

    socket.onclose = () => {
      console.log("WebSocket fermé");
      stopRecording();
    };
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
    
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      // Envoyer la transcription complète pour traitement par Bedrock
      socketRef.current.send(JSON.stringify({ type: "process", text: fullTranscriptRef.current }));
    }
    
    setIsRecording(false);
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      }
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.close();
      }
    };
  }, []);

  return (
    <div className="app-shell" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', gap: '16px', height: '100%', overflowY: 'auto', padding: '20px', boxSizing: 'border-box' }}>
      <div style={{ textAlign: 'center', flexShrink: 0 }}>
        <h2 style={{ margin: '0 0 4px 0' }}>Agent IA Vocal</h2>
        <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-subtle)' }}>Assistant vocal en mode demo, avec orb et etats d'ecoute/parole.</p>
      </div>
      
      <div 
        ref={sttContainerRef}
        style={{
        width: '100%',
        maxWidth: '600px',
        height: '80px',
        padding: '16px',
        background: 'var(--glass-2)',
        borderRadius: '12px',
        border: '1px solid var(--stroke)',
        overflowY: 'auto',
        boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.05)',
        textAlign: 'left',
        flexShrink: 0
      }}>
        {!isRecording && !sttText.final && !sttText.partial ? (
          <span style={{ color: 'var(--text-subtle)', fontStyle: 'italic' }}>En attente de la voix...</span>
        ) : (
          <>
            <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{sttText.final}</span>
            <span style={{ color: 'var(--text-subtle)' }}>{sttText.partial}</span>
          </>
        )}
      </div>

      <div 
        ref={agentContainerRef}
        style={{
        width: '100%',
        maxWidth: '600px',
        height: '150px',
        padding: '16px',
        background: 'rgba(0, 136, 255, 0.08)',
        borderRadius: '12px',
        border: '1px solid rgba(0, 136, 255, 0.2)',
        color: 'var(--tahoe-accent)',
        fontWeight: 500,
        textAlign: 'left',
        overflowY: 'auto',
        lineHeight: '1.5',
        flexShrink: 0
      }}>
        <em>{agentText}</em>
      </div>

      <button 
        onClick={toggleRecording}
        style={{
          marginTop: '10px',
          padding: '14px 36px',
          fontSize: '1.05rem',
          cursor: 'pointer',
          borderRadius: '24px',
          border: 'none',
          background: isRecording ? '#ff5f56' : 'var(--tahoe-accent)',
          color: 'white',
          transition: 'all 0.3s ease',
          fontWeight: 600,
          boxShadow: isRecording ? '0 0 16px rgba(255, 95, 86, 0.4)' : '0 4px 12px rgba(0, 136, 255, 0.3)',
          flexShrink: 0
        }}
      >
        {isRecording ? "Arrêter l'écoute" : "Démarrer l'écoute"}
      </button>
    </div>
  );
}
