import { AnimatePresence, motion } from 'framer-motion';
import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { useOsStore } from '../../store/osStore';

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function IconMic() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="12" y1="19" x2="12" y2="22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="8" y1="22" x2="16" y2="22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function IconPlus() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 5v14M5 12h14"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconSearch() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="2" />
      <path d="M16 16l4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function IconPaperclip() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M8.5 14.5L15 8a2.5 2.5 0 0 0-3.5-3.5L5 11a4 4 0 1 0 5.7 5.7l6.3-6.3a5.5 5.5 0 0 0-7.8-7.8l-1 1"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconSend() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 18V8m-4.5 4.5L12 8l4.5 4.5"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconDownload() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 4v11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M8 12l4 4 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 20h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M6 12l4 4 8-9"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

interface AttachmentMeta {
  name: string;
  pages: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  attachment?: AttachmentMeta;
}

const API_BASE = 'http://localhost:8000';

const SEED_MESSAGES: ChatMessage[] = [
  {
    id: 'seed-welcome',
    role: 'assistant',
    content: 'Bonjour ! Je suis Campus Co-Pilot. Demande-moi de résumer tes cours, gérer tes deadlines ou réserver une salle.',
  },
];

interface StatusEvent {
  agent: string;
  status: 'running' | 'done' | 'fallback';
  label: string;
}

const AGENT_LABELS: Record<string, string> = {
  moodle: '📚',
  agenda: '📅',
  room:   '🏫',
};

export default function TUMCopilot() {
  const openWindow = useOsStore((state) => state.openWindow);
  const hintId = useId();
  const sessionId = useRef(uid());
  const [messages, setMessages] = useState<ChatMessage[]>(SEED_MESSAGES);
  const [draft, setDraft] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [statusEvents, setStatusEvents] = useState<StatusEvent[]>([]);
  const [downloadedIds, setDownloadedIds] = useState<Set<string>>(() => new Set());
  const [attachMenuOpen, setAttachMenuOpen] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const plusWrapRef = useRef<HTMLDivElement>(null);

  const showHint = useCallback((text: string) => {
    setHint(text);
    window.setTimeout(() => setHint(null), 2600);
  }, []);

  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, scrollToBottom]);

  useEffect(() => {
    if (!attachMenuOpen) return;
    const onDown = (e: MouseEvent) => {
      if (plusWrapRef.current && !plusWrapRef.current.contains(e.target as Node)) {
        setAttachMenuOpen(false);
      }
    };
    window.addEventListener('mousedown', onDown);
    return () => window.removeEventListener('mousedown', onDown);
  }, [attachMenuOpen]);

  const send = async () => {
    const text = draft.trim();
    if (!text || isTyping) return;
    setDraft('');
    setAttachMenuOpen(false);
    setMessages((prev) => [...prev, { id: uid(), role: 'user', content: text }]);
    setIsTyping(true);
    setStatusEvents([]);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId.current }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: { response: string; agents_called: string[]; status_events: StatusEvent[] } = await res.json();

      setStatusEvents(data.status_events ?? []);
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: 'assistant', content: data.response },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: 'assistant',
          content: '⚠️ Impossible de joindre le serveur. Vérifie que le backend tourne sur le port 8000.',
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      send();
    }
  };

  const onDownload = (messageId: string) => {
    setDownloadedIds((prev) => {
      const next = new Set(prev);
      next.add(messageId);
      return next;
    });
    showHint('Simulated download — file integration coming soon.');
  };

  return (
    <div className="copilot-chat">
      <div
        ref={scrollRef}
        className="copilot-chat-scroll"
        role="log"
        aria-label="Conversation TUM Copilot"
        aria-live="polite"
      >
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 12, scale: 0.985 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ type: 'spring', stiffness: 520, damping: 38 }}
              className={`copilot-msg-row copilot-msg-row--${msg.role === 'user' ? 'user' : 'assistant'}`}
            >
              <div
                className={`copilot-bubble copilot-bubble--${msg.role === 'user' ? 'user' : 'assistant'}`}
              >
                {msg.role === 'assistant' ? (
                  <p className="copilot-bubble-text">{msg.content}</p>
                ) : (
                  msg.content
                )}
                {msg.attachment && (
                  <div className="copilot-attachment-card">
                    <div className="copilot-attachment-icon" aria-hidden>
                      PDF
                    </div>
                    <div className="copilot-attachment-meta">
                      <span className="copilot-attachment-name">{msg.attachment.name}</span>
                      <span className="copilot-attachment-detail">{msg.attachment.pages}</span>
                    </div>
                    <button
                      type="button"
                      className={`copilot-attachment-action ${
                        downloadedIds.has(msg.id) ? 'copilot-attachment-action--done' : ''
                      }`}
                      aria-label={
                        downloadedIds.has(msg.id) ? 'Downloaded' : 'Download'
                      }
                      onClick={() => onDownload(msg.id)}
                    >
                      {downloadedIds.has(msg.id) ? <IconCheck /> : <IconDownload />}
                    </button>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        <AnimatePresence>
          {isTyping && (
            <motion.div
              key="typing"
              className="copilot-msg-row copilot-msg-row--assistant"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.18 }}
            >
              {statusEvents.length > 0 ? (
                <div className="copilot-status-events">
                  {statusEvents.map((ev, i) => (
                    <span
                      key={i}
                      className={`copilot-status-pill copilot-status-pill--${ev.status}`}
                      title={ev.agent}
                    >
                      {AGENT_LABELS[ev.agent] ?? '🤖'} {ev.label}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="copilot-typing" aria-hidden>
                  <span className="copilot-typing-dot" />
                  <span className="copilot-typing-dot" />
                  <span className="copilot-typing-dot" />
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="copilot-input-area">
        {hint && (
          <p id={`${hintId}-hint`} className="copilot-ephemeral-hint" role="status">
            {hint}
          </p>
        )}
        <footer className="copilot-input-wrap">
          <div className="copilot-input-bar">
            <div className="copilot-plus-anchor" ref={plusWrapRef}>
              <button
                type="button"
                className={`copilot-input-plus ${attachMenuOpen ? 'copilot-input-plus--open' : ''}`}
                aria-expanded={attachMenuOpen}
                aria-haspopup="menu"
                aria-label="More options"
                onClick={() => setAttachMenuOpen((o) => !o)}
              >
                <IconPlus />
              </button>
              <AnimatePresence>
                {attachMenuOpen && (
                  <motion.div
                    role="menu"
                    className="copilot-attach-menu"
                    initial={{ opacity: 0, y: 6, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 4, scale: 0.98 }}
                    transition={{ duration: 0.16 }}
                  >
                    <button
                      type="button"
                      role="menuitem"
                      className="copilot-attach-menu-item"
                      onClick={() => {
                        setAttachMenuOpen(false);
                        showHint('File import — coming soon.');
                      }}
                    >
                      Import file
                    </button>
                    <button
                      type="button"
                      role="menuitem"
                      className="copilot-attach-menu-item"
                      onClick={() => {
                        setAttachMenuOpen(false);
                        showHint('Capture — coming soon.');
                      }}
                    >
                      Take a photo
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            <input
              className="copilot-input-field"
              type="text"
              placeholder="Message TUM Copilot…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onKeyDown}
              autoComplete="off"
              disabled={isTyping}
              aria-describedby={hint ? `${hintId}-hint` : undefined}
            />
            <div className="copilot-input-actions">
              {draft.trim() ? (
                <button
                  type="button"
                  className="copilot-input-send"
                  aria-label="Send"
                  onClick={send}
                  disabled={isTyping}
                >
                  <IconSend />
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    className="copilot-input-icon"
                    aria-label="Search"
                    onClick={() => showHint('Search in conversation — soon.')}
                  >
                    <IconSearch />
                  </button>
                  <button
                    type="button"
                    className="copilot-input-icon"
                    aria-label="Attachment"
                    onClick={() => showHint('Attachments — use the + menu or here soon.')}
                  >
                    <IconPaperclip />
                  </button>
                  <button
                    type="button"
                    className="copilot-input-icon"
                    aria-label="Open TUM Voice"
                    onClick={() => openWindow('voice')}
                    style={{ color: 'var(--tahoe-accent)' }}
                  >
                    <IconMic />
                  </button>
                </>
              )}
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
