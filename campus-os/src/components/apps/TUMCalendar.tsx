import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface CalendarEvent {
  summary: string;
  start: string;
  end: string;
  location: string;
}

export default function TUMCalendar() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [openMenuIndex, setOpenMenuIndex] = useState<number | null>(null);
  const [currentWeekOffset, setCurrentWeekOffset] = useState(0);
  const [newEvent, setNewEvent] = useState({
    summary: '',
    start_time: '',
    end_time: '',
    location: ''
  });

  // Calcul de la plage de dates pour la semaine actuelle
  const getWeekRange = (offset: number) => {
    const now = new Date();
    const start = new Date(now);
    start.setDate(now.getDate() - now.getDay() + 1 + (offset * 7)); // Lundi
    start.setHours(0, 0, 0, 0);
    
    const end = new Date(start);
    end.setDate(start.getDate() + 6); // Dimanche
    end.setHours(23, 59, 59, 999);
    
    return { start, end };
  };

  const { start: weekStart, end: weekEnd } = getWeekRange(currentWeekOffset);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/calendar');
      const data = await response.json();
      setEvents(data);
    } catch (error) {
      console.error("Erreur lors de la récupération du calendrier:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const handleAddEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:8000/api/calendar/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newEvent),
      });
      if (response.ok) {
        setShowAddModal(false);
        setNewEvent({ summary: '', start_time: '', end_time: '', location: '' });
        fetchEvents();
      }
    } catch (error) {
      console.error("Erreur lors de l'ajout de l'événement:", error);
    }
  };

  const handleDeleteEvent = async (summary: string, start: string) => {
    if (!window.confirm(`Supprimer l'événement "${summary}" ?`)) return;
    try {
      const response = await fetch('http://localhost:8000/api/calendar/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary, start_time: start }),
      });
      if (response.ok) {
        setOpenMenuIndex(null);
        fetchEvents();
      }
    } catch (error) {
      console.error("Erreur lors de la suppression:", error);
    }
  };

  // Filtrer les événements pour la semaine sélectionnée
  const filteredEvents = events.filter(event => {
    const eventDate = new Date(event.start);
    return eventDate >= weekStart && eventDate <= weekEnd;
  });

  const formatDate = (isoStr: string) => {
    const date = new Date(isoStr);
    return date.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric' });
  };

  const formatTime = (isoStr: string) => {
    const date = new Date(isoStr);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="calendar-app app-shell" style={{ 
      display: 'flex', flexDirection: 'column', height: '100%', padding: 0, 
      background: 'rgba(255,255,255,0.85)', color: '#1d1d1f', overflow: 'hidden' 
    }}>
      {/* Header Interne avec Navigation Semaine */}
      <header style={{ 
        padding: '12px 20px', display: 'flex', justifyContent: 'space-between', 
        alignItems: 'center', borderBottom: '1px solid rgba(0,0,0,0.1)',
        background: 'rgba(255,255,255,0.7)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <div style={{ display: 'flex', gap: '5px' }}>
            <button onClick={() => setCurrentWeekOffset(prev => prev - 1)} style={{ border: 'none', background: '#F0F0F2', borderRadius: '6px', padding: '5px 10px', cursor: 'pointer' }}>{"<"}</button>
            <button onClick={() => setCurrentWeekOffset(0)} style={{ border: 'none', background: '#F0F0F2', borderRadius: '6px', padding: '5px 10px', cursor: 'pointer', fontSize: '11px', fontWeight: 600 }}>Aujourd'hui</button>
            <button onClick={() => setCurrentWeekOffset(prev => prev + 1)} style={{ border: 'none', background: '#F0F0F2', borderRadius: '6px', padding: '5px 10px', cursor: 'pointer' }}>{">"}</button>
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>Semaine du {weekStart.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}</h2>
          </div>
        </div>
        
        <button 
          onClick={() => setShowAddModal(true)}
          style={{ 
            background: '#007AFF', color: 'white', border: 'none', 
            borderRadius: '8px', padding: '6px 14px', fontWeight: 600, cursor: 'pointer',
            fontSize: '13px'
          }}
        >
          + Événement
        </button>
      </header>

      {/* Liste filtrée */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '15px' }} onClick={() => setOpenMenuIndex(null)}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>Chargement...</div>
        ) : filteredEvents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#888', fontSize: '14px' }}>Aucun événement cette semaine</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {filteredEvents.map((event, i) => (
              <motion.div 
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                key={i}
                style={{ 
                  padding: '10px 14px', borderRadius: '10px', 
                  background: 'white', border: '1px solid rgba(0,0,0,0.05)',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  position: 'relative'
                }}
              >
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center', minWidth: 0, flex: 1 }}>
                  <div style={{ 
                    width: '3px', height: '30px', borderRadius: '2px', flexShrink: 0,
                    background: event.summary.includes('Réservation') ? '#FF9500' : '#007AFF'
                  }} />
                  <div style={{ overflow: 'hidden' }}>
                    <div style={{ fontWeight: 600, fontSize: '13px', color: '#000', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{event.summary}</div>
                    <div style={{ fontSize: '11px', color: '#666' }}>{event.location}</div>
                  </div>
                </div>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ textAlign: 'right', minWidth: '70px' }}>
                    <div style={{ fontWeight: 600, fontSize: '11px', color: '#000' }}>{formatDate(event.start)}</div>
                    <div style={{ fontSize: '10px', color: '#999' }}>{formatTime(event.start)}</div>
                  </div>

                  {/* Menu Trois Points */}
                  <div style={{ position: 'relative' }}>
                    <button 
                      onClick={(e) => { e.stopPropagation(); setOpenMenuIndex(openMenuIndex === i ? null : i); }}
                      style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: '5px', fontSize: '18px', color: '#AAA' }}
                    >
                      ⋮
                    </button>
                    
                    <AnimatePresence>
                      {openMenuIndex === i && (
                        <motion.div 
                          initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
                          style={{ 
                            position: 'absolute', right: 0, top: '30px', background: 'white', 
                            boxShadow: '0 4px 12px rgba(0,0,0,0.15)', borderRadius: '8px', padding: '5px', zIndex: 50,
                            minWidth: '120px', border: '1px solid rgba(0,0,0,0.05)'
                          }}
                        >
                          <button 
                            onClick={() => handleDeleteEvent(event.summary, event.start)}
                            style={{ 
                              width: '100%', padding: '8px 12px', border: 'none', background: 'transparent', 
                              textAlign: 'left', color: '#FF3B30', cursor: 'pointer', fontSize: '12px', fontWeight: 600,
                              borderRadius: '4px'
                            }}
                            onMouseOver={(e) => e.currentTarget.style.background = '#FFF1F0'}
                            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
                          >
                            Supprimer
                          </button>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Modal d'ajout (Style Apple épuré et ultra-net) */}
      <AnimatePresence>
        {showAddModal && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{ 
              position: 'absolute', inset: 0, 
              background: 'rgba(0,0,0,0.5)', // Fond plus sombre pour focus
              display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 
            }}
          >
            <motion.form 
              initial={{ scale: 0.95, y: 10 }} animate={{ scale: 1, y: 0 }}
              onSubmit={handleAddEvent}
              style={{ 
                padding: '32px', width: '400px', borderRadius: '24px', 
                background: '#FFFFFF', 
                boxShadow: '0 30px 60px rgba(0,0,0,0.3)',
                display: 'flex', flexDirection: 'column', gap: '20px', 
                color: '#000', border: '1px solid rgba(0,0,0,0.1)'
              }}
            >
              <h3 style={{ margin: 0, fontSize: '22px', fontWeight: 700, textAlign: 'center' }}>Nouvel événement</h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '11px', fontWeight: 700, color: '#666', letterSpacing: '0.5px' }}>TITRE</label>
                <input 
                  type="text" placeholder="Réunion, Cours, etc." required
                  value={newEvent.summary} onChange={e => setNewEvent({...newEvent, summary: e.target.value})}
                  style={{ 
                    padding: '12px 15px', borderRadius: '12px', border: '1px solid #DDD', 
                    background: '#F9F9F9', color: '#000', fontSize: '15px', width: '100%', boxSizing: 'border-box'
                  }}
                />
              </div>

              {/* Dates empilées pour éviter les débordements */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '11px', fontWeight: 700, color: '#666', letterSpacing: '0.5px' }}>DATE DE DÉBUT</label>
                  <input 
                    type="datetime-local" required
                    value={newEvent.start_time} onChange={e => setNewEvent({...newEvent, start_time: e.target.value})}
                    style={{ 
                      padding: '12px 15px', borderRadius: '12px', border: '1px solid #DDD', 
                      background: '#F9F9F9', color: '#000', fontSize: '15px', width: '100%', boxSizing: 'border-box'
                    }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '11px', fontWeight: 700, color: '#666', letterSpacing: '0.5px' }}>DATE DE FIN</label>
                  <input 
                    type="datetime-local" required
                    value={newEvent.end_time} onChange={e => setNewEvent({...newEvent, end_time: e.target.value})}
                    style={{ 
                      padding: '12px 15px', borderRadius: '12px', border: '1px solid #DDD', 
                      background: '#F9F9F9', color: '#000', fontSize: '15px', width: '100%', boxSizing: 'border-box'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '11px', fontWeight: 700, color: '#666', letterSpacing: '0.5px' }}>LIEU (OPTIONNEL)</label>
                <input 
                  type="text" placeholder="Lieu"
                  value={newEvent.location} onChange={e => setNewEvent({...newEvent, location: e.target.value})}
                  style={{ 
                    padding: '12px 15px', borderRadius: '12px', border: '1px solid #DDD', 
                    background: '#F9F9F9', color: '#000', fontSize: '15px', width: '100%', boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '10px' }}>
                <button 
                  type="button" 
                  onClick={() => setShowAddModal(false)} 
                  style={{ 
                    flex: 1, padding: '14px', borderRadius: '14px', border: 'none', 
                    background: '#F0F0F0', color: '#000', fontWeight: 600, cursor: 'pointer', fontSize: '15px'
                  }}
                >
                  Annuler
                </button>
                <button 
                  type="submit" 
                  style={{ 
                    flex: 1, padding: '14px', borderRadius: '14px', border: 'none', 
                    background: '#007AFF', color: 'white', fontWeight: 600, cursor: 'pointer', fontSize: '15px'
                  }}
                >
                  Ajouter
                </button>
              </div>
            </motion.form>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
