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

  // Time-Grid Settings
  const START_HOUR = 8;
  const END_HOUR = 21;
  const HOUR_HEIGHT = 60; // pixels per hour

  const getWeekRange = (offset: number) => {
    const now = new Date();
    const start = new Date(now);
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1) + (offset * 7);
    start.setDate(diff);
    start.setHours(0, 0, 0, 0);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    end.setHours(23, 59, 59, 999);
    return { start, end };
  };

  const { start: weekStart, end: weekEnd } = getWeekRange(currentWeekOffset);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      await fetch('http://localhost:8000/api/calendar/sync', { method: 'POST' });
      const response = await fetch('http://localhost:8000/api/calendar');
      const data = await response.json();
      setEvents(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error fetching events:", error);
    } finally {
      setLoading(false);
    }
  };

  // Usage of loading to avoid ESLint warning
  useEffect(() => {
    fetchEvents();
  }, [currentWeekOffset]);

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
      } else {
        alert("Failed to add event. Please check the details.");
      }
    } catch (error) {
      console.error("Error adding event:", error);
    }
  };

  const handleDeleteEvent = async (summary: string, start: string) => {
    if (!window.confirm(`Delete "${summary}"?`)) return;
    try {
      const response = await fetch('http://localhost:8000/api/calendar/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary, start_time: start }),
      });
      if (response.ok) {
        setOpenMenuIndex(null);
        fetchEvents();
      } else {
        alert("Failed to delete event.");
      }
    } catch (error) {
      console.error("Error deleting event:", error);
    }
  };

  const filteredEvents = events.filter(event => {
    const eventDate = new Date(event.start);
    return eventDate >= weekStart && eventDate <= weekEnd;
  });

  const getEventsByDay = () => {
    const grouped: { [key: number]: CalendarEvent[] } = { 1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 0: [] };
    filteredEvents.forEach(event => {
      const day = new Date(event.start).getDay();
      if (grouped[day]) grouped[day].push(event);
    });
    return grouped;
  };

  const getEventStyle = (event: CalendarEvent) => {
    const startDate = new Date(event.start);
    const endDate = new Date(event.end);
    const startHour = startDate.getHours() + startDate.getMinutes() / 60;
    const endHour = endDate.getHours() + endDate.getMinutes() / 60;
    const duration = endHour - startHour;

    return {
      top: `${(startHour - START_HOUR) * HOUR_HEIGHT}px`,
      height: `${Math.max(duration * HOUR_HEIGHT, 25)}px`,
      position: 'absolute' as const,
      left: '4px',
      right: '4px',
      zIndex: 10
    };
  };

  const formatTime = (isoStr: string) => {
    const date = new Date(isoStr);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const dayIndices = [1, 2, 3, 4, 5, 6, 0];
  const eventsByDay = getEventsByDay();

  return (
    <div className="calendar-app app-shell" style={{ 
      display: 'flex', flexDirection: 'column', height: '100%', padding: 0, 
      background: 'white', color: '#1d1d1f', overflow: 'hidden',
      fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif'
    }}>
      {/* Header */}
      <header style={{ 
        padding: '12px 20px', display: 'flex', justifyContent: 'space-between', 
        alignItems: 'center', borderBottom: '1px solid #E5E5E7', background: '#FFF', zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <button onClick={() => setCurrentWeekOffset(prev => prev - 1)} style={{ border: 'none', background: '#F2F2F7', borderRadius: '8px', padding: '8px 12px', cursor: 'pointer' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="black" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
          </button>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: '220px' }}>
            <h2 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: '#000' }}>
              Week of {weekStart.toLocaleDateString('en-US', { day: 'numeric', month: 'short' })} — {weekEnd.toLocaleDateString('en-US', { day: 'numeric', month: 'short' })}
            </h2>
          </div>
          <button onClick={() => setCurrentWeekOffset(prev => prev + 1)} style={{ border: 'none', background: '#F2F2F7', borderRadius: '8px', padding: '8px 12px', cursor: 'pointer' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="black" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6"/></svg>
          </button>
        </div>
        <button onClick={() => setShowAddModal(true)} style={{ background: '#007AFF', color: 'white', border: 'none', borderRadius: '8px', padding: '8px 16px', fontWeight: 600, cursor: 'pointer' }}>+ Event</button>
      </header>

      {/* Grid Container */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} onClick={() => setOpenMenuIndex(null)}>
        {/* Days Row */}
        <div style={{ display: 'grid', gridTemplateColumns: '50px repeat(7, 1fr)', borderBottom: '1px solid #E5E5E7', background: '#FAFAFA' }}>
          <div style={{ borderRight: '1px solid #E5E5E7' }} />
          {daysOfWeek.map((day, i) => {
            const date = new Date(weekStart);
            date.setDate(weekStart.getDate() + i);
            const isToday = new Date().toDateString() === date.toDateString();
            return (
              <div key={day} style={{ padding: '8px', textAlign: 'center', borderRight: i < 6 ? '1px solid #E5E5E7' : 'none' }}>
                <div style={{ fontSize: '10px', fontWeight: 600, color: isToday ? '#007AFF' : '#86868B' }}>{day.toUpperCase()}</div>
                <div style={{ fontSize: '16px', fontWeight: 500, color: isToday ? '#007AFF' : 'inherit' }}>{date.getDate()}</div>
              </div>
            );
          })}
        </div>

        {/* Time Grid Scrollable */}
        <div style={{ flex: 1, overflowY: 'auto', position: 'relative', display: 'flex' }}>
          {/* Time Labels Column */}
          <div style={{ width: '50px', borderRight: '1px solid #E5E5E7', background: '#FAFAFA', flexShrink: 0 }}>
            {Array.from({ length: END_HOUR - START_HOUR + 1 }).map((_, i) => (
              <div key={i} style={{ height: `${HOUR_HEIGHT}px`, borderBottom: '1px solid #F2F2F7', position: 'relative' }}>
                <span style={{ position: 'absolute', top: '-10px', left: '0', right: '0', textAlign: 'center', fontSize: '9px', color: '#86868B' }}>
                  {START_HOUR + i}:00
                </span>
              </div>
            ))}
          </div>

          {/* Grid with Columns and Hour Lines */}
          <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', position: 'relative' }}>
            <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
              {Array.from({ length: END_HOUR - START_HOUR + 1 }).map((_, i) => (
                <div key={i} style={{ height: '1px', background: '#F2F2F7', width: '100%', position: 'absolute', top: `${(i + 1) * HOUR_HEIGHT}px` }} />
              ))}
            </div>

            {dayIndices.map((dayNum, i) => (
              <div key={dayNum} style={{ borderRight: i < 6 ? '1px solid #F2F2F7' : 'none', position: 'relative', height: `${(END_HOUR - START_HOUR + 1) * HOUR_HEIGHT}px` }}>
                {eventsByDay[dayNum].map((event, idx) => {
                  const menuId = dayNum * 100 + idx;
                  const startH = new Date(event.start).getHours();
                  if (startH < START_HOUR || startH > END_HOUR) return null;

                  return (
                    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} key={idx} style={{ 
                        ...getEventStyle(event), padding: '4px 6px', borderRadius: '4px',
                        background: event.summary.includes('Booking') || event.summary.includes('Reservation') ? 'rgba(255, 149, 0, 0.12)' : 'rgba(0, 122, 255, 0.12)',
                        borderLeft: `2px solid ${event.summary.includes('Booking') || event.summary.includes('Reservation') ? '#FF9500' : '#007AFF'}`,
                        boxShadow: '0 1px 3px rgba(0,0,0,0.05)', overflow: 'hidden'
                      }}>
                      <div style={{ 
                        fontWeight: 700, fontSize: '10px', lineHeight: '1.2', 
                        whiteSpace: 'normal', overflow: 'hidden', paddingRight: '12px',
                        wordBreak: 'break-word'
                      }}>
                        {event.summary}
                      </div>
                      <button onClick={(e) => { e.stopPropagation(); setOpenMenuIndex(openMenuIndex === menuId ? null : menuId); }} style={{ position: 'absolute', top: '2px', right: '2px', border: 'none', background: 'transparent', cursor: 'pointer', color: '#888', fontSize: '12px' }}>⋮</button>
                      <AnimatePresence>
                        {openMenuIndex === menuId && (
                          <motion.div initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} style={{ position: 'absolute', right: 0, top: '20px', background: 'white', boxShadow: '0 4px 12px rgba(0,0,0,0.15)', borderRadius: '6px', padding: '4px', zIndex: 100, border: '1px solid #E5E5E7' }}>
                            <button onClick={() => handleDeleteEvent(event.summary, event.start)} style={{ width: '100%', padding: '6px 12px', border: 'none', background: 'transparent', color: '#FF3B30', fontSize: '10px', fontWeight: 600, cursor: 'pointer' }}>Delete</button>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Add Modal */}
      <AnimatePresence>
        {showAddModal && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200 }}>
            <motion.form initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} onSubmit={handleAddEvent} style={{ padding: '30px', width: '400px', borderRadius: '24px', background: '#FFFFFF', display: 'flex', flexDirection: 'column', gap: '20px', boxShadow: '0 20px 40px rgba(0,0,0,0.15)', border: '1px solid rgba(0,0,0,0.05)' }}>
              <h3 style={{ margin: 0, fontSize: '20px', fontWeight: 700, textAlign: 'center', color: '#000' }}>New Event</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '11px', fontWeight: 700, color: '#86868B', marginLeft: '4px' }}>EVENT TITLE</label>
                <input 
                  type="text" 
                  placeholder="Lecture, Meeting, etc." 
                  required 
                  value={newEvent.summary} 
                  onChange={e => setNewEvent({ ...newEvent, summary: e.target.value })} 
                  onInvalid={e => (e.target as HTMLInputElement).setCustomValidity('Please fill out this field')}
                  onInput={e => (e.target as HTMLInputElement).setCustomValidity('')}
                  style={{ padding: '12px 16px', borderRadius: '12px', border: '1px solid #E5E5E7', background: '#F5F5F7', fontSize: '14px', outline: 'none', color: '#000' }} 
                />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '11px', fontWeight: 700, color: '#86868B', marginLeft: '4px' }}>START TIME</label>
                  <input 
                    type="datetime-local" 
                    placeholder="dd/mm/aaaa"
                    required 
                    value={newEvent.start_time} 
                    onChange={e => setNewEvent({ ...newEvent, start_time: e.target.value })} 
                    onInvalid={e => (e.target as HTMLInputElement).setCustomValidity('Please fill out this field')}
                    onInput={e => (e.target as HTMLInputElement).setCustomValidity('')}
                    style={{ padding: '10px 12px', borderRadius: '12px', border: '1px solid #E5E5E7', background: '#F5F5F7', fontSize: '13px', outline: 'none', color: '#000' }} 
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '11px', fontWeight: 700, color: '#86868B', marginLeft: '4px' }}>END TIME</label>
                  <input 
                    type="datetime-local" 
                    placeholder="dd/mm/aaaa"
                    required 
                    value={newEvent.end_time} 
                    onChange={e => setNewEvent({ ...newEvent, end_time: e.target.value })} 
                    onInvalid={e => (e.target as HTMLInputElement).setCustomValidity('Please fill out this field')}
                    onInput={e => (e.target as HTMLInputElement).setCustomValidity('')}
                    style={{ padding: '10px 12px', borderRadius: '12px', border: '1px solid #E5E5E7', background: '#F5F5F7', fontSize: '13px', outline: 'none', color: '#000' }} 
                  />
                </div>
              </div>
              <div style={{ display: 'flex', gap: '12px', marginTop: '10px' }}>
                <button type="button" onClick={() => setShowAddModal(false)} style={{ flex: 1, padding: '14px', borderRadius: '14px', border: 'none', background: '#F2F2F7', color: '#000', fontWeight: 600, cursor: 'pointer', fontSize: '14px' }}>Cancel</button>
                <button type="submit" style={{ flex: 1, padding: '14px', borderRadius: '14px', border: 'none', background: '#007AFF', color: 'white', fontWeight: 600, cursor: 'pointer', fontSize: '14px' }}>Add Event</button>
              </div>
            </motion.form>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
