// JARVIS 3D Network Topology
// Three.js visualization of homelab infrastructure

class NetworkTopology {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) return;

    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.nodes = [];
    this.connections = [];
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    this.isRotating = true;
    this.selectedNode = null;

    // Homelab infrastructure definition
    this.infrastructure = [
      { id: 'udm', name: 'UDM SE', ip: '192.168.10.1', type: 'router', status: 'up', x: 0, y: 2, z: 0 },
      { id: 'pve1', name: 'Proxmox 1', ip: '192.168.10.50', type: 'server', status: 'up', x: -3, y: 0, z: -1 },
      { id: 'pve2', name: 'Proxmox 2', ip: '192.168.10.51', type: 'server', status: 'up', x: 3, y: 0, z: -1 },
      { id: 'nas', name: 'Synology NAS', ip: '192.168.10.249', type: 'storage', status: 'up', x: 0, y: 0, z: -3 },
      { id: 'jarvis', name: 'JARVIS', ip: '192.168.10.100', type: 'service', status: 'up', x: -2, y: -1, z: 1 },
      { id: 'monitoring', name: 'Monitoring', ip: '192.168.10.104', type: 'service', status: 'down', x: 2, y: -1, z: 1 },
      { id: 'n8n', name: 'n8n', ip: '192.168.10.200', type: 'service', status: 'up', x: 0, y: -2, z: 2 }
    ];

    // Connections between nodes
    this.connectionDefs = [
      ['udm', 'pve1'], ['udm', 'pve2'], ['udm', 'nas'], ['udm', 'jarvis'], ['udm', 'monitoring'], ['udm', 'n8n'],
      ['pve1', 'nas'], ['pve2', 'nas'],
      ['jarvis', 'n8n'], ['jarvis', 'monitoring']
    ];

    this.init();
  }

  init() {
    // Scene setup
    this.scene = new THREE.Scene();

    // Camera
    const aspect = this.container.clientWidth / this.container.clientHeight;
    this.camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 1000);
    this.camera.position.set(0, 3, 8);
    this.camera.lookAt(0, 0, 0);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.container.appendChild(this.renderer.domElement);

    // Ambient light
    const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
    this.scene.add(ambientLight);

    // Point light
    const pointLight = new THREE.PointLight(0x00d4ff, 1, 100);
    pointLight.position.set(0, 5, 5);
    this.scene.add(pointLight);

    // Create nodes
    this.createNodes();

    // Create connections
    this.createConnections();

    // Create grid
    this.createGrid();

    // Event listeners
    this.setupEventListeners();

    // Start animation
    this.animate();
  }

  createNodes() {
    const typeColors = {
      router: 0x00d4ff,
      server: 0xff6b35,
      storage: 0x9d4edd,
      service: 0x00ff88
    };

    const typeGeometries = {
      router: new THREE.OctahedronGeometry(0.4),
      server: new THREE.BoxGeometry(0.5, 0.5, 0.5),
      storage: new THREE.CylinderGeometry(0.3, 0.3, 0.5, 8),
      service: new THREE.SphereGeometry(0.3, 16, 16)
    };

    this.infrastructure.forEach(node => {
      const color = typeColors[node.type] || 0x00d4ff;
      const geometry = typeGeometries[node.type] || new THREE.SphereGeometry(0.3, 16, 16);

      // Main mesh
      const material = new THREE.MeshPhongMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: node.status === 'up' ? 0.3 : 0.1,
        transparent: true,
        opacity: node.status === 'up' ? 0.9 : 0.4
      });

      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(node.x, node.y, node.z);
      mesh.userData = node;

      // Glow effect
      const glowGeometry = new THREE.SphereGeometry(0.5, 16, 16);
      const glowMaterial = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: node.status === 'up' ? 0.15 : 0.05
      });
      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      mesh.add(glow);

      // Label sprite
      const label = this.createLabel(node.name);
      label.position.set(0, 0.7, 0);
      mesh.add(label);

      this.scene.add(mesh);
      this.nodes.push(mesh);
    });
  }

  createLabel(text) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 256;
    canvas.height = 64;

    context.fillStyle = 'rgba(0, 0, 0, 0)';
    context.fillRect(0, 0, canvas.width, canvas.height);

    context.font = 'bold 24px Arial';
    context.fillStyle = '#00d4ff';
    context.textAlign = 'center';
    context.fillText(text, 128, 40);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(material);
    sprite.scale.set(2, 0.5, 1);

    return sprite;
  }

  createConnections() {
    const material = new THREE.LineBasicMaterial({
      color: 0x00d4ff,
      transparent: true,
      opacity: 0.3
    });

    this.connectionDefs.forEach(([fromId, toId]) => {
      const fromNode = this.infrastructure.find(n => n.id === fromId);
      const toNode = this.infrastructure.find(n => n.id === toId);

      if (fromNode && toNode) {
        const points = [
          new THREE.Vector3(fromNode.x, fromNode.y, fromNode.z),
          new THREE.Vector3(toNode.x, toNode.y, toNode.z)
        ];

        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(geometry, material);

        this.scene.add(line);
        this.connections.push(line);
      }
    });
  }

  createGrid() {
    const gridHelper = new THREE.GridHelper(10, 20, 0x00d4ff, 0x003344);
    gridHelper.position.y = -3;
    gridHelper.material.transparent = true;
    gridHelper.material.opacity = 0.2;
    this.scene.add(gridHelper);
  }

  setupEventListeners() {
    // Mouse move for hover detection
    this.container.addEventListener('mousemove', (e) => {
      const rect = this.container.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    });

    // Click for selection
    this.container.addEventListener('click', (e) => {
      this.checkIntersection(true);
    });

    // Mouse enter/leave for rotation control
    this.container.addEventListener('mouseenter', () => {
      this.isRotating = false;
    });

    this.container.addEventListener('mouseleave', () => {
      this.isRotating = true;
      this.resetHighlights();
    });

    // Resize handler
    window.addEventListener('resize', () => {
      const width = this.container.clientWidth;
      const height = this.container.clientHeight;
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(width, height);
    });
  }

  checkIntersection(isClick = false) {
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(this.nodes);

    // Reset all highlights
    this.resetHighlights();

    if (intersects.length > 0) {
      const node = intersects[0].object;
      this.highlightNode(node);

      if (isClick && node.userData) {
        this.showNodeDetails(node.userData);
      }
    }
  }

  highlightNode(node) {
    node.material.emissiveIntensity = 0.8;
    node.scale.set(1.2, 1.2, 1.2);
    this.container.style.cursor = 'pointer';
  }

  resetHighlights() {
    this.nodes.forEach(node => {
      node.material.emissiveIntensity = node.userData.status === 'up' ? 0.3 : 0.1;
      node.scale.set(1, 1, 1);
    });
    this.container.style.cursor = 'default';
  }

  showNodeDetails(node) {
    // Show node details in a toast or panel
    const detail = document.createElement('div');
    detail.className = 'topology-tooltip';
    detail.innerHTML = '<strong>' + node.name + '</strong><br>' +
      'IP: ' + node.ip + '<br>' +
      'Type: ' + node.type + '<br>' +
      'Status: <span class="' + node.status + '">' + node.status.toUpperCase() + '</span>';

    // Position near cursor
    detail.style.left = (event.clientX + 10) + 'px';
    detail.style.top = (event.clientY + 10) + 'px';

    document.body.appendChild(detail);

    // Remove after 3 seconds
    setTimeout(() => {
      detail.remove();
    }, 3000);
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    // Auto-rotate when not hovering
    if (this.isRotating) {
      this.scene.rotation.y += 0.002;
    }

    // Check for hover intersections
    if (!this.isRotating) {
      this.checkIntersection();
    }

    // Pulse effect on nodes
    const time = Date.now() * 0.001;
    this.nodes.forEach((node, i) => {
      if (node.userData.status === 'up') {
        node.children[0].material.opacity = 0.1 + Math.sin(time * 2 + i) * 0.05;
      }
    });

    this.renderer.render(this.scene, this.camera);
  }

  destroy() {
    if (this.renderer) {
      this.container.removeChild(this.renderer.domElement);
      this.renderer.dispose();
    }
  }
}

// Export for use
window.NetworkTopology = NetworkTopology;

// Dynamic topology loading
NetworkTopology.prototype.loadLiveData = async function() {
  try {
    const response = await fetch('/api/topology');
    const data = await response.json();

    if (data.nodes && data.nodes.length > 0) {
      // Update infrastructure
      this.infrastructure = data.nodes.map(n => ({
        id: n.id,
        name: n.name,
        ip: n.ip || '',
        type: n.type,
        status: n.status || 'up',
        x: n.x || 0,
        y: n.y || 0,
        z: n.z || 0,
        cpu: n.cpu,
        memory: n.memory
      }));

      this.connectionDefs = data.connections || [];

      // Rebuild scene
      this.rebuildScene();
    }
  } catch (e) {
    console.error('Failed to load topology data:', e);
  }
};

NetworkTopology.prototype.rebuildScene = function() {
  // Remove existing nodes and connections
  this.nodes.forEach(n => {
    if (n.mesh) this.scene.remove(n.mesh);
    if (n.label) this.scene.remove(n.label);
    if (n.glow) this.scene.remove(n.glow);
  });
  this.connections.forEach(c => {
    if (c.line) this.scene.remove(c.line);
  });

  this.nodes = [];
  this.connections = [];

  // Recreate
  this.createNodes();
  this.createConnections();
};

// Auto-load live data when topology opens
const originalShowTopology = JarvisHUD.prototype.showTopology;
JarvisHUD.prototype.showTopology = function() {
  document.getElementById('overlay').classList.add('visible');
  document.getElementById('topologyContainer').classList.add('visible');

  if (!this.topology) {
    this.topology = new NetworkTopology('topologyCanvas');
  }

  // Load live data
  if (this.topology.loadLiveData) {
    this.topology.loadLiveData();
  }
};
