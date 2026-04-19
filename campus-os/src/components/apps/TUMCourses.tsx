import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

const COURSES_DATA: Record<string, string[]> = {
  'DataScience_EarthObservation': ['Lecture_1_SS26.json'],
  'Data_Science_in_Earth_Observation': ['Lecture_1_SS26_.json'],
  'Deutsch_als_Fremdsprache_B1.1_(Lechle_GERMAN_MATTERS_GAR)_(SoSe_2026)': ['Sprich_mit__Poster-2.json'],
  'Einführung_in_die_Kern-,_Teilchen-_und_Astrophysik_(in_englischer_Sprache)': ['Exercise_Sheet_1.json', 'PH8016_Lectures_L1-L3_nuclei_SS2026_v1.json'],
  'Introduction_to_Deep_Learning_(IN2346)': ['1.Intro.json', 'tutorial-1.json'],
  'Space_Exploration': ['SX01_Introduction_SS26.json', 'SX_SS26_E_01_Introduction_Problem.json']
};

export default function TUMCourses() {
  const courses = Object.keys(COURSES_DATA);
  const [activeCourse, setActiveCourse] = useState(courses[0]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [summaryContent, setSummaryContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Clean the string for better display (replace underscores with spaces)
  const cleanName = (name: string) => name.replace(/_/g, ' ');

  useEffect(() => {
    if (!activeFile || !activeCourse) {
      setSummaryContent(null);
      return;
    }
    
    setLoading(true);
    setSummaryContent(null);

    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
    const host = window.location.hostname === 'localhost' && window.location.port === '3000' 
      ? 'localhost:8000' 
      : window.location.host;
    
    const url = `${protocol}//${host}/api/summary/${encodeURIComponent(activeCourse)}/${encodeURIComponent(activeFile)}`;
    
    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (data.summary) {
          setSummaryContent(data.summary);
        } else {
          setSummaryContent("Erreur : Résumé introuvable. " + (data.error || ""));
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Fetch error:", err);
        setSummaryContent("Erreur de connexion au serveur.");
        setLoading(false);
      });
  }, [activeCourse, activeFile]);

  return (
    <div className="app-shell" style={{ display: 'flex', flexDirection: 'row', height: '100%', padding: 0, overflow: 'hidden' }}>
      
      {/* Sidebar / Menu de gauche */}
      <div style={{ 
        width: '280px', 
        borderRight: '1px solid var(--stroke)', 
        background: 'var(--glass-2)',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto'
      }}>
        <div style={{ padding: '16px', borderBottom: '1px solid var(--stroke)', position: 'sticky', top: 0, background: 'var(--glass-2)', zIndex: 10 }}>
          <h2 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--text-main)' }}>📚 Mes Cours</h2>
        </div>
        <div style={{ padding: '8px' }}>
          {courses.map(course => (
            <button
              key={course}
              onClick={() => { setActiveCourse(course); setActiveFile(null); }}
              style={{
                width: '100%',
                textAlign: 'left',
                padding: '12px',
                marginBottom: '4px',
                borderRadius: '8px',
                border: 'none',
                background: activeCourse === course ? 'var(--tahoe-accent)' : 'transparent',
                color: activeCourse === course ? 'white' : 'var(--text-main)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                fontWeight: activeCourse === course ? 600 : 400,
                fontSize: '0.85rem',
                lineHeight: '1.4'
              }}
              title={cleanName(course)}
            >
              {cleanName(course).substring(0, 45)}{course.length > 45 ? '...' : ''}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content / Zone de texte */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto', padding: '32px', background: 'var(--glass-1)' }}>
        <h1 style={{ margin: '0 0 24px 0', fontSize: '1.8rem', color: 'var(--text-main)' }}>{cleanName(activeCourse)}</h1>
        
        <h3 style={{ margin: '0 0 16px 0', color: 'var(--text-subtle)', fontSize: '1rem' }}>Documents et Résumés générés :</h3>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '24px' }}>
          {COURSES_DATA[activeCourse].map(file => (
            <button
              key={file}
              onClick={() => setActiveFile(file)}
              style={{
                padding: '10px 16px',
                borderRadius: '20px',
                border: '1px solid',
                borderColor: activeFile === file ? 'var(--tahoe-accent)' : 'var(--stroke)',
                background: activeFile === file ? 'rgba(0, 136, 255, 0.1)' : 'var(--glass-3)',
                color: activeFile === file ? 'var(--tahoe-accent)' : 'var(--text-main)',
                cursor: 'pointer',
                fontWeight: 500,
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              📄 {file.replace('.json', '')}
            </button>
          ))}
        </div>

        {/* Content Viewer / Afficheur de texte */}
        <div style={{
          flex: 1,
          background: 'var(--glass-3)',
          borderRadius: '12px',
          border: '1px solid var(--stroke)',
          padding: '24px',
          overflowY: 'auto',
          minHeight: '200px',
          boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.05)'
        }}>
          {activeFile ? (
            <div>
              <h2 style={{ marginTop: 0, color: 'var(--text-main)' }}>Résumé : {activeFile.replace('.json', '')}</h2>
              <div style={{ width: '100%', height: '1px', background: 'var(--stroke)', marginBottom: '16px' }} />
              <div className="markdown-container">
                {loading ? 'Chargement du résumé...' : (
                  summaryContent ? <ReactMarkdown>{summaryContent}</ReactMarkdown> : 'Aucun contenu disponible.'
                )}
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-subtle)', fontStyle: 'italic' }}>
              Sélectionnez un document ci-dessus pour lire son résumé.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
