import math
import random
import time
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QPoint, QPropertyAnimation, QEasingCurve, Qt
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QRadialGradient

class Particle:
    """Represents a single particle in the particle system."""
    
    def __init__(self, x, y, color=None, size=None, velocity=None, life=None):
        self.x = x
        self.y = y
        self.color = color or QColor(random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        self.size = size or random.uniform(2, 6)
        self.velocity_x = velocity[0] if velocity else random.uniform(-2, 2)
        self.velocity_y = velocity[1] if velocity else random.uniform(-2, 2)
        self.life = life or random.uniform(0.5, 2.0)
        self.max_life = self.life
        self.alpha = 255
        self.gravity = 0.1
        self.friction = 0.98
        
    def update(self, dt):
        """Update particle position and life."""
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.velocity_y += self.gravity
        self.velocity_x *= self.friction
        self.velocity_y *= self.friction
        
        self.life -= dt
        self.alpha = int((self.life / self.max_life) * 255)
        
        return self.life > 0

class ParticleSystem(QWidget):
    """A widget that displays animated particles following the mouse."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.mouse_pos = QPoint(0, 0)
        self.last_emission = 0
        self.emission_rate = 0.05  # seconds between emissions
        
        # Set up the widget
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setProperty("class", "particle-system")
        
        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(16)  # ~60 FPS
        
    def mouse_move_event(self, pos):
        """Handle mouse movement to update particle emission position."""
        if not self.window() or not self.window().isActiveWindow():
            return

        self.mouse_pos = pos
        current_time = time.time()
        
        if current_time - self.last_emission >= self.emission_rate:
            self.emit_particles(pos)
            self.last_emission = current_time
    
    def emit_particles(self, pos, count=3):
        """Emit new particles at the given position."""
        if not self.window() or not self.window().isActiveWindow():
            return
            
        for _ in range(count):
            particle = Particle(
                pos.x(), pos.y(),
                color=QColor(random.randint(150, 255), random.randint(150, 255), random.randint(150, 255)),
                size=random.uniform(1, 4),
                velocity=(random.uniform(-1, 1), random.uniform(-1, 1)),
                life=random.uniform(0.8, 1.5)
            )
            self.particles.append(particle)
    
    def update_particles(self):
        """Update all particles and remove dead ones."""
        if not self.window() or not self.window().isActiveWindow():
            if self.particles: # Clear only if there are particles
                self.particles.clear()
                self.update() # Schedule a repaint to clear them from screen
            return

        dt = 0.016  # Approximate delta time for 60 FPS
        
        # Update particles
        alive_particles = []
        for particle in self.particles:
            if particle.update(dt):
                alive_particles.append(particle)
        
        self.particles = alive_particles
        self.update()
    
    def paintEvent(self, event):
        """Paint all particles."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for particle in self.particles:
            # Create gradient for particle
            gradient = QRadialGradient(particle.x, particle.y, particle.size)
            color = QColor(particle.color)
            color.setAlpha(particle.alpha)
            gradient.setColorAt(0, color)
            gradient.setColorAt(1, QColor(0, 0, 0, 0))
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(particle.x - particle.size), int(particle.y - particle.size), 
                              int(particle.size * 2), int(particle.size * 2))

class AnimatedButton(QPushButton):
    """A button with hover animations and particle effects that respects QSS."""
    
    # The 'clicked' signal is inherited from QPushButton.
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.particles = []
        
        self.setCursor(Qt.PointingHandCursor)

        # Timer for particle animation
        self.particle_timer = QTimer(self)
        self.particle_timer.timeout.connect(self.update_particles)
        self.particle_timer.start(16) # ~60 FPS
        
    # setText, text, and setEnabled are inherited.
        
    def enterEvent(self, event):
        """Handle mouse enter event."""
        super().enterEvent(event)
        self.emit_particles()
        
    def leaveEvent(self, event):
        """Handle mouse leave event."""
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        """Handle mouse press event."""
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.emit_particles(count=8)
            
    # mouseReleaseEvent is inherited and correctly handles the click signal.
            
    def emit_particles(self, count=5):
        """Emit particles from the button."""
        if not self.window() or not self.window().isActiveWindow():
            return

        for _ in range(count):
            particle = Particle(
                random.randint(0, self.width()),
                random.randint(0, self.height()),
                color=QColor(255, 255, 255, 180),
                size=random.uniform(1, 3),
                velocity=(random.uniform(-3, 3), random.uniform(-3, 3)),
                life=random.uniform(0.5, 1.0)
            )
            self.particles.append(particle)

    def update_particles(self):
        """Met à jour les particules et repeint le widget si nécessaire."""
        if not self.window() or not self.window().isActiveWindow():
            if self.particles:
                self.particles.clear()
                self.update()
            return

        if not self.particles:
            return

        alive_particles = [p for p in self.particles if p.update(0.016)]
        
        if len(alive_particles) != len(self.particles):
            self.particles = alive_particles
            self.update()
        elif self.particles:
            self.update()

    def paintEvent(self, event):
        """Paint the button using QSS and then draw particles on top."""
        # Let the base QPushButton draw itself first. This will apply the QSS styles.
        super().paintEvent(event)
        
        # Now, draw our particles over the button.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.particles:
            for particle in self.particles:
                gradient = QRadialGradient(particle.x, particle.y, particle.size)
                color = QColor(particle.color)
                color.setAlpha(particle.alpha)
                gradient.setColorAt(0, color)
                gradient.setColorAt(1, QColor(0, 0, 0, 0))
                
                painter.setBrush(QBrush(gradient))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(int(particle.x - particle.size), int(particle.y - particle.size), 
                                  int(particle.size * 2), int(particle.size * 2))

class LoadingSpinner(QWidget):
    """An animated loading spinner with particle effects."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.particles = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(50)
        
    def update_animation(self):
        """Update the spinner animation."""
        if not self.window() or not self.window().isActiveWindow():
            return # Ne fait rien si la fenêtre n'est pas active

        self.angle = (self.angle + 10) % 360
        
        # Emit particles occasionally
        if random.random() < 0.3:
            self.emit_particles()
            
        self.update()
        
    def emit_particles(self):
        """Emit particles from the spinner."""
        if not self.window() or not self.window().isActiveWindow():
            return

        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(self.width(), self.height()) / 4
        
        for _ in range(2):
            angle = random.uniform(0, 2 * math.pi)
            x = center_x + math.cos(angle) * radius
            y = center_y + math.sin(angle) * radius
            
            particle = Particle(
                x, y,
                color=QColor(100, 150, 255),
                size=random.uniform(1, 3),
                velocity=(random.uniform(-1, 1), random.uniform(-1, 1)),
                life=random.uniform(0.5, 1.0)
            )
            self.particles.append(particle)
    
    def paintEvent(self, event):
        """Paint the loading spinner."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(self.width(), self.height()) / 4
        
        # Draw spinner
        for i in range(8):
            angle = self.angle + (i * 45)
            alpha = 255 - (i * 30)
            if alpha < 0:
                alpha = 0
                
            color = QColor(100, 150, 255, alpha)
            painter.setPen(QPen(color, 3))
            
            x1 = center_x + math.cos(math.radians(angle)) * (radius - 10)
            y1 = center_y + math.sin(math.radians(angle)) * (radius - 10)
            x2 = center_x + math.cos(math.radians(angle)) * radius
            y2 = center_y + math.sin(math.radians(angle)) * radius
            
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        # Draw particles
        if self.window() and self.window().isActiveWindow():
            for particle in self.particles[:]:
                if particle.update(0.05):
                    gradient = QRadialGradient(particle.x, particle.y, particle.size)
                    color = QColor(particle.color)
                    color.setAlpha(particle.alpha)
                    gradient.setColorAt(0, color)
                    gradient.setColorAt(1, QColor(0, 0, 0, 0))
                    
                    painter.setBrush(QBrush(gradient))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(int(particle.x - particle.size), int(particle.y - particle.size), 
                                      int(particle.size * 2), int(particle.size * 2))
                else:
                    self.particles.remove(particle) 