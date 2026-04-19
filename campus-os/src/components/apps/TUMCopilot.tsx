import { AnimatePresence, motion } from 'framer-motion';
import { useCallback, useEffect, useId, useRef, useState } from 'react';

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
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

const SEED_MESSAGES: ChatMessage[] = [
  {
    id: 'seed-1',
    role: 'user',
    content:
      'Résume les points importants du polycopié « Systèmes d\'exploitation » pour la semaine prochaine.',
  },
  {
    id: 'seed-2',
    role: 'assistant',
    content:
      "Voici l'essentiel : processus et threads, appels système, ordonnancement préemptif, mémoire virtuelle et pagination. Les exercices Moodle sur les diagrammes d'états sont recommandés avant le quiz.",
    attachment: { name: 'Resume_OS_Week4.pdf', pages: '3 pages' },
  },
  {
    id: 'seed-3',
    role: 'user',
    content: 'Ajoute une question type examen sur la pagination.',
  },
];

const MOCK_REPLIES: Array<{ text: string; attachment?: AttachmentMeta }> = [
  {
    text: "Bien reçu. Pour la pagination, pense à expliquer la différence entre défaut de page et temps d'accès disque.",
  },
  {
    text: "Je peux t'aider à structurer une fiche : intro, définitions, exemple avec TLB, pièges fréquents.",
    attachment: { name: 'Fiche_Pagination.pdf', pages: '2 pages' },
  },
  {
    text: "Si tu veux, envoie le sujet exact du partiel et j'adapte le niveau de détail.",
  },
  {
    text: "Astuce : entraîne-toi à estimer le nombre de défauts de page pour une chaîne de références donnée.",
  },
];

export default function TUMCopilot() {
  const hintId = useId();
  const [messages, setMessages] = useState<ChatMessage[]>(SEED_MESSAGES);
  const [draft, setDraft] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [mockRound, setMockRound] = useState(0);
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

  const send = () => {
    const text = draft.trim();
    if (!text || isTyping) return;
    setDraft('');
    setAttachMenuOpen(false);
    setMessages((prev) => [...prev, { id: uid(), role: 'user', content: text }]);
    setIsTyping(true);

    const delay = 950 + Math.random() * 700;
    const reply = MOCK_REPLIES[mockRound % MOCK_REPLIES.length];
    setMockRound((n) => n + 1);

    window.setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: 'assistant',
          content: reply.text,
          attachment: reply.attachment,
        },
      ]);
      setIsTyping(false);
    }, delay);
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
    showHint('Téléchargement simulé — intégration fichier à venir.');
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
                        downloadedIds.has(msg.id) ? 'Téléchargé' : 'Télécharger'
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
              <div className="copilot-typing" aria-hidden>
                <span className="copilot-typing-dot" />
                <span className="copilot-typing-dot" />
                <span className="copilot-typing-dot" />
              </div>
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
                aria-label="Plus d’options"
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
                        showHint('Import de fichier — bientôt disponible.');
                      }}
                    >
                      Importer un fichier
                    </button>
                    <button
                      type="button"
                      role="menuitem"
                      className="copilot-attach-menu-item"
                      onClick={() => {
                        setAttachMenuOpen(false);
                        showHint('Capture — bientôt disponible.');
                      }}
                    >
                      Prendre une photo
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
                  aria-label="Envoyer"
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
                    aria-label="Rechercher"
                    onClick={() => showHint('Recherche dans la conversation — bientôt.')}
                  >
                    <IconSearch />
                  </button>
                  <button
                    type="button"
                    className="copilot-input-icon"
                    aria-label="Pièce jointe"
                    onClick={() => showHint('Pièces jointes — utilise le menu + ou ici bientôt.')}
                  >
                    <IconPaperclip />
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
