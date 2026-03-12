import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

fig = plt.figure(figsize=(6, 6))
ax = fig.add_subplot(111, projection='3d')

# --- Sfera ---
u = np.linspace(0, 2 * np.pi, 200)
v = np.linspace(0, np.pi, 200)
sx = np.outer(np.cos(u), np.sin(v))
sy = np.outer(np.sin(u), np.sin(v))
sz = np.outer(np.ones(np.size(u)), np.cos(v))
ax.plot_surface(sx, sy, sz, color='lightcyan', alpha=0.15, zorder=0)

# --- Wireframe meridiani/paralleli ---
for angle in np.linspace(0, np.pi, 7):
    x = np.sin(v) * np.cos(angle)
    y = np.sin(v) * np.sin(angle)
    z = np.cos(v)
    ax.plot(x, y, z, color='steelblue', lw=0.4, alpha=0.4)
for angle in np.linspace(0, 2*np.pi, 13):
    x = np.sin(angle) * np.sin(u)
    y = np.cos(angle) * np.sin(u)
    z = np.cos(u)
    ax.plot(x, y, z, color='steelblue', lw=0.4, alpha=0.4)

# --- Assi ---
ax.quiver(0,0,-1.4, 0,0,2.9, arrow_length_ratio=0.06, color='gray', lw=1.2)
ax.quiver(-1.4,0,0, 2.9,0,0, arrow_length_ratio=0.06, color='gray', lw=1.2)
ax.quiver(0,-1.4,0, 0,2.9,0, arrow_length_ratio=0.06, color='gray', lw=1.2)

# --- Etichette assi ---
ax.text(0, 0,  1.65, r'$|0\rangle$', ha='center', va='bottom', fontsize=13, color='black')
ax.text(0, 0, -1.65, r'$|1\rangle$', ha='center', va='top',    fontsize=13, color='black')
ax.text( 1.65, 0, 0, r'$|+\rangle$', ha='left',   va='center', fontsize=12, color='black')
ax.text(-1.65, 0, 0, r'$|-\rangle$', ha='right',  va='center', fontsize=12, color='black')
ax.text(0,  1.65, 0, r'$|i\rangle$', ha='center', va='center', fontsize=12, color='black')
ax.text(0, -1.65, 0, r'$|-i\rangle$',ha='center', va='center', fontsize=12, color='black')

# --- Vettore di stato generico ---
theta = np.pi / 3
phi   = np.pi / 4
x_s = np.sin(theta) * np.cos(phi)
y_s = np.sin(theta) * np.sin(phi)
z_s = np.cos(theta)
ax.quiver(0,0,0, x_s,y_s,z_s, arrow_length_ratio=0.1,
          color='crimson', lw=2.5, label=r'$|\psi\rangle$')
ax.text(x_s*1.12, y_s*1.12, z_s*1.12, r'$|\psi\rangle$',
        fontsize=12, color='crimson')

# --- Archi angoli theta e phi ---
t_arc = np.linspace(0, theta, 60)
ax.plot(np.sin(t_arc)*np.cos(phi)*0.35,
        np.sin(t_arc)*np.sin(phi)*0.35,
        np.cos(t_arc)*0.35, color='navy', lw=1.2)
ax.text(0.12*np.cos(phi/2), 0.12*np.sin(phi/2), 0.42,
        r'$\theta$', fontsize=11, color='navy')

p_arc = np.linspace(0, phi, 60)
r_eq  = 0.38
ax.plot(r_eq*np.cos(p_arc), r_eq*np.sin(p_arc),
        np.zeros(60), color='darkgreen', lw=1.2)
ax.text(r_eq*np.cos(phi/2)*1.15, r_eq*np.sin(phi/2)*1.15, -0.05,
        r'$\varphi$', fontsize=11, color='darkgreen')

# --- Proiezione sull'equatore ---
ax.plot([0, x_s], [0, y_s], [0, 0], 'k--', lw=0.8, alpha=0.5)
ax.plot([x_s, x_s], [y_s, y_s], [0, z_s], 'k--', lw=0.8, alpha=0.5)

ax.set_xlim([-1.5, 1.5])
ax.set_ylim([-1.5, 1.5])
ax.set_zlim([-1.5, 1.5])
ax.set_box_aspect([1,1,1])
ax.axis('off')

plt.tight_layout()
plt.savefig('bloch_sphere.pdf', dpi=300, bbox_inches='tight',
            facecolor='white', format='pdf')
plt.savefig('bloch_sphere.png', dpi=300, bbox_inches='tight',
            facecolor='white')
print("Bloch sphere saved.")
