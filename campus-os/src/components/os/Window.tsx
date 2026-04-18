import { MouseEvent as ReactMouseEvent, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { WindowState, useOsStore } from '../../store/osStore';
import TrafficLights from './TrafficLights';

interface WindowProps {
  windowData: WindowState;
  children: React.ReactNode;
}

export default function Window({ windowData, children }: WindowProps) {
  const focusWindow = useOsStore((state) => state.focusWindow);
  const closeWindow = useOsStore((state) => state.closeWindow);
  const updateWindow = useOsStore((state) => state.updateWindow);
  const toggleMaximize = useOsStore((state) => state.toggleMaximize);
  const [isDragging, setIsDragging] = useState(false);
  const dragOffset = useRef({ x: 0, y: 0 });

  const startDrag = (event: ReactMouseEvent<HTMLElement>) => {
    if (windowData.isMaximized) return;
    event.preventDefault();
    focusWindow(windowData.id);
    setIsDragging(true);
    dragOffset.current = {
      x: event.clientX - windowData.x,
      y: event.clientY - windowData.y,
    };

    const onMove = (moveEvent: MouseEvent) => {
      const DOCK_HEIGHT = 84;
      const MENU_BAR_HEIGHT = 36;
      
      let nextX = Math.max(0, moveEvent.clientX - dragOffset.current.x);
      let nextY = Math.max(MENU_BAR_HEIGHT, moveEvent.clientY - dragOffset.current.y);
      
      let nextWidth = windowData.width;
      let nextHeight = windowData.height;

      if (nextX + nextWidth > window.innerWidth) {
        nextWidth = Math.max(300, window.innerWidth - nextX);
      }
      
      if (nextY + nextHeight > window.innerHeight - DOCK_HEIGHT) {
        nextHeight = Math.max(200, window.innerHeight - DOCK_HEIGHT - nextY);
      }
      
      updateWindow(windowData.id, { x: nextX, y: nextY, width: nextWidth, height: nextHeight });
    };

    const onUp = () => {
      setIsDragging(false);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  return (
    <motion.article
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ 
        opacity: 1, 
        scale: 1, 
        x: windowData.x,
        y: windowData.y,
        width: windowData.width,
        height: windowData.height,
      }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={isDragging ? { duration: 0 } : { type: 'spring', stiffness: 300, damping: 25 }}
      className={`window glass-panel ${windowData.isMaximized ? 'maximized' : ''}`}
      onMouseDown={() => focusWindow(windowData.id)}
      style={{
        zIndex: windowData.zIndex,
        position: 'absolute',
        top: 0,
        left: 0,
      }}
    >
      <div className="window-header" onMouseDown={startDrag} onDoubleClick={() => toggleMaximize(windowData.id)}>
        <TrafficLights 
          onClose={() => closeWindow(windowData.id)} 
          onMaximize={() => toggleMaximize(windowData.id)}
        />
        <div className="window-toolbar-pill" />
        <span className="window-title">{windowData.title}</span>
      </div>
      <div className="window-body">{children}</div>
    </motion.article>
  );
}
