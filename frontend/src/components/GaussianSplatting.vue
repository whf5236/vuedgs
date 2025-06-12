<template>
  <div class="splat-container">
    <canvas ref="canvas" class="splat-canvas"></canvas>
    <div v-if="isLoading" class="spinner-container">
      <div class="cube-wrapper">
        <div class="cube">
          <div class="cube-faces">
            <div class="cube-face bottom"></div>
            <div class="cube-face top"></div>
            <div class="cube-face left"></div>
            <div class="cube-face right"></div>
            <div class="cube-face back"></div>
            <div class="cube-face front"></div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="message" class="message-container">
      <p>{{ message }}</p>
    </div>
    <div class="info-overlay">
      <div id="fps">{{ fps }} fps</div>
      <div id="camid">Vertices: {{ vertexCount.toLocaleString() }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GaussianSplatting',
  props: {
    selectedFile: {
      type: Object,
      default: null,
    },
  },
  data() {
    return {
      gl: null,
      worker: null,
      program: null,
      viewMatrix: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
      projectionMatrix: null,
      camera: {
        fx: 1160,
        fy: 1160,
        width: 1920,
        height: 1080,
      },
      vertexCount: 0,
      isLoading: false,
      message: '',
      fps: 0,
      lastFrameTime: 0,
      // Camera interaction state
      mouseState: {
        down: false,
        startX: 0,
        startY: 0,
      },
      // Keep track of animation frame
      animationFrameId: null,
    };
  },
  computed: {
    username() {
      return this.$store.getters.user?.username || 'default_user';
    }
  },
  watch: {
    selectedFile(newFile) {
      if (newFile && newFile.name && (newFile.name.endsWith('.splat') || newFile.name.endsWith('.ply'))) {
        this.loadFile(newFile);
      } else {
        this.message = 'Please select a .splat or .ply file.';
        this.vertexCount = 0;
        this.cleanupScene();
      }
    },
  },
  mounted() {
    this.initWebGL();
    this.initWorker();
    window.addEventListener('resize', this.handleResize);

    const canvas = this.$refs.canvas;
    canvas.addEventListener('mousedown', this.onMouseDown);
    canvas.addEventListener('mousemove', this.onMouseMove);
    canvas.addEventListener('mouseup', this.onMouseUp);
    canvas.addEventListener('mouseout', this.onMouseUp); // Stop when mouse leaves canvas
    canvas.addEventListener('wheel', this.onWheel, { passive: false });
  },
  beforeUnmount() {
    this.cleanup();
  },
  methods: {
    //
    // INITIALIZATION
    //
    initWebGL() {
      try {
        const canvas = this.$refs.canvas;
        this.gl = canvas.getContext('webgl2', { antialias: false });
        const gl = this.gl;

        const vertexShaderSource = `#version 300 es
                  precision highp float;
                  precision highp int;

                  uniform highp usampler2D u_texture;
                  uniform mat4 projection, view;
                  uniform vec2 focal;
                  uniform vec2 viewport;

                  in vec2 position;
                  in int index;

                  out vec4 vColor;
                  out vec2 vPosition;

                  void main () {
                      uvec4 cen = texelFetch(u_texture, ivec2((uint(index) & 0x3ffu) << 1, uint(index) >> 10), 0);
                      vec4 cam = view * vec4(uintBitsToFloat(cen.xyz), 1);
                      vec4 pos2d = projection * cam;

                      float clip = 1.2 * pos2d.w;
                      if (pos2d.z < -clip || pos2d.x < -clip || pos2d.x > clip || pos2d.y < -clip || pos2d.y > clip) {
                          gl_Position = vec4(0.0, 0.0, 2.0, 1.0);
                          return;
                      }

                      uvec4 cov = texelFetch(u_texture, ivec2(((uint(index) & 0x3ffu) << 1) | 1u, uint(index) >> 10), 0);
                      vec2 u1 = unpackHalf2x16(cov.x), u2 = unpackHalf2x16(cov.y), u3 = unpackHalf2x16(cov.z);
                      mat3 Vrk = mat3(u1.x, u1.y, u2.x, u1.y, u2.y, u3.x, u2.x, u3.x, u3.y);

                      mat3 J = mat3(
                          focal.x / cam.z, 0., -(focal.x * cam.x) / (cam.z * cam.z),
                          0., -focal.y / cam.z, (focal.y * cam.y) / (cam.z * cam.z),
                          0., 0., 0.
                      );

                      mat3 T = transpose(mat3(view)) * J;
                      mat3 cov2d = transpose(T) * Vrk * T;

                      float mid = (cov2d[0][0] + cov2d[1][1]) / 2.0;
                      float radius = length(vec2((cov2d[0][0] - cov2d[1][1]) / 2.0, cov2d[0][1]));
                      float lambda1 = mid + radius, lambda2 = mid - radius;

                      if(lambda2 < 0.0) return;
                      vec2 diagonalVector = normalize(vec2(cov2d[0][1], lambda1 - cov2d[0][0]));
                      vec2 majorAxis = min(sqrt(2.0 * lambda1), 1024.0) * diagonalVector;
                      vec2 minorAxis = min(sqrt(2.0 * lambda2), 1024.0) * vec2(diagonalVector.y, -diagonalVector.x);

                      vColor = clamp(pos2d.z/pos2d.w+1.0, 0.0, 1.0) * vec4((cov.w) & 0xffu, (cov.w >> 8) & 0xffu, (cov.w >> 16) & 0xffu, (cov.w >> 24) & 0xffu) / 255.0;
                      vPosition = position;

                      vec2 vCenter = vec2(pos2d) / pos2d.w;
                      gl_Position = vec4(
                          vCenter
                          + position.x * majorAxis / viewport
                          + position.y * minorAxis / viewport, 0.0, 1.0);

                  }`;

        const fragmentShaderSource = `#version 300 es
                  precision highp float;
                  in vec4 vColor;
                  in vec2 vPosition;
                  out vec4 fragColor;
                  void main () {
                      float A = -dot(vPosition, vPosition);
                      if (A < -4.0) discard;
                      float B = exp(A) * vColor.a;
                      fragColor = vec4(B * vColor.rgb, B);
                  }`;

        const vertexShader = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vertexShader, vertexShaderSource);
        gl.compileShader(vertexShader);
        if (!gl.getShaderParameter(vertexShader, gl.COMPILE_STATUS)) {
          throw new Error('Vertex Shader Error: ' + gl.getShaderInfoLog(vertexShader));
        }

        const fragmentShader = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fragmentShader, fragmentShaderSource);
        gl.compileShader(fragmentShader);
        if (!gl.getShaderParameter(fragmentShader, gl.COMPILE_STATUS)) {
          throw new Error('Fragment Shader Error: ' + gl.getShaderInfoLog(fragmentShader));
        }

        this.program = gl.createProgram();
        gl.attachShader(this.program, vertexShader);
        gl.attachShader(this.program, fragmentShader);
        gl.linkProgram(this.program);
        gl.useProgram(this.program);
        if (!gl.getProgramParameter(this.program, gl.LINK_STATUS)) {
          throw new Error('Program Link Error: ' + gl.getProgramInfoLog(this.program));
        }

        gl.disable(gl.DEPTH_TEST);
        gl.enable(gl.BLEND);
        gl.blendFuncSeparate(gl.ONE_MINUS_DST_ALPHA, gl.ONE, gl.ONE_MINUS_DST_ALPHA, gl.ONE);
        gl.blendEquationSeparate(gl.FUNC_ADD, gl.FUNC_ADD);

        // Setup buffers
        const triangleVertices = new Float32Array([-2, -2, 2, -2, 2, 2, -2, 2]);
        const vertexBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, triangleVertices, gl.STATIC_DRAW);
        const a_position = gl.getAttribLocation(this.program, 'position');
        gl.enableVertexAttribArray(a_position);
        gl.vertexAttribPointer(a_position, 2, gl.FLOAT, false, 0, 0);

        const indexBuffer = gl.createBuffer();
        const a_index = gl.getAttribLocation(this.program, 'index');
        gl.enableVertexAttribArray(a_index);
        gl.bindBuffer(gl.ARRAY_BUFFER, indexBuffer);
        gl.vertexAttribIPointer(a_index, 1, gl.INT, false, 0, 0);
        gl.vertexAttribDivisor(a_index, 1);
        this.buffers = { vertexBuffer, indexBuffer };

        const texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, texture);
        const u_textureLocation = gl.getUniformLocation(this.program, 'u_texture');
        gl.uniform1i(u_textureLocation, 0);
        this.texture = texture;

        this.uniforms = {
          u_projection: gl.getUniformLocation(this.program, 'projection'),
          u_viewport: gl.getUniformLocation(this.program, 'viewport'),
          u_focal: gl.getUniformLocation(this.program, 'focal'),
          u_view: gl.getUniformLocation(this.program, 'view'),
        };
        
        this.viewMatrix = this.invert4([
          0.47, 0.04, 0.88, 0, 
          -0.11, 0.99, 0.02, 0, 
          -0.88, -0.11, 0.47, 0, 
          -1.07, 0.03, 6.55, 1,
        ]);


        this.handleResize();
      } catch (e) {
        this.message = e.message;
        console.error(e);
      }
    },

    initWorker() {
      this.worker = new Worker('/splat-worker.js');
      this.worker.onmessage = (e) => {
        if (e.data.buffer) {
          this.isLoading = false;
          this.message = '';
          const splatData = new Uint8Array(e.data.buffer);
          this.vertexCount = Math.floor(splatData.length / (3 * 4 + 3 * 4 + 4 + 4));
        } else if (e.data.texdata) {
          const { texdata, texwidth, texheight } = e.data;
          const gl = this.gl;
          gl.bindTexture(gl.TEXTURE_2D, this.texture);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
          gl.texImage2D(
              gl.TEXTURE_2D, 0, gl.RGBA32UI, texwidth, texheight, 0, 
              gl.RGBA_INTEGER, gl.UNSIGNED_INT, new Uint32Array(texdata)
          );
          gl.activeTexture(gl.TEXTURE0);
          gl.bindTexture(gl.TEXTURE_2D, this.texture);
        } else if (e.data.depthIndex) {
          const { depthIndex, viewProj } = e.data;
          this.vertexCount = e.data.vertexCount;
          const gl = this.gl;
          gl.bindBuffer(gl.ARRAY_BUFFER, this.buffers.indexBuffer);
          gl.bufferData(gl.ARRAY_BUFFER, new Uint32Array(depthIndex), gl.DYNAMIC_DRAW);
        }
      };
    },
    
    //
    // DATA LOADING
    //
    async loadFile(file) {
      if (!file) return;
      this.cleanupScene();
      this.isLoading = true;
      this.message = `Loading ${file.name}...`;

      try {
        const fileUrl = `http://localhost:5000/api/download/${this.username}/${file.name}`;
        const req = await fetch(fileUrl);
        if (req.status !== 200) {
          throw new Error(`Failed to load file: ${req.status} ${req.statusText}`);
        }
        const fileData = await req.arrayBuffer();
        
        this.message = 'Processing file...';
        
        if (file.name.endsWith('.splat')) {
          this.worker.postMessage({ buffer: fileData, vertexCount: Math.floor(fileData.byteLength / (3 * 4 + 3 * 4 + 4 + 4)) });
        } else if (file.name.endsWith('.ply')) {
           this.worker.postMessage({ ply: fileData, save: false });
        }
        
        if (!this.animationFrameId) {
            this.frame();
        }

      } catch (err) {
        this.message = err.message;
        this.isLoading = false;
        console.error(err);
      }
    },

    //
    // RENDERING LOOP
    //
    frame() {
      this.animationFrameId = requestAnimationFrame(this.frame);

      const now = performance.now();
      const delta = now - this.lastFrameTime;
      if (delta > 0) {
        this.fps = (1000 / delta).toFixed(0);
      }
      this.lastFrameTime = now;
      
      const gl = this.gl;
      if (!gl || this.vertexCount === 0) {
          if (gl) {
            gl.clear(gl.COLOR_BUFFER_BIT);
          }
          return;
      }
      
      const viewProj = this.multiply4(this.projectionMatrix, this.viewMatrix);
      this.worker.postMessage({ view: viewProj });

      gl.uniformMatrix4fv(this.uniforms.u_view, false, this.viewMatrix);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArraysInstanced(gl.TRIANGLE_FAN, 0, 4, this.vertexCount);
    },

    //
    // EVENT HANDLERS & CAMERA
    //
    handleResize() {
      const canvas = this.$refs.canvas;
      const container = canvas.parentElement;
      if (!container) return;

      const devicePixelRatio = window.devicePixelRatio || 1;
      const width = container.clientWidth;
      const height = container.clientHeight;

      canvas.width = Math.round(width * devicePixelRatio);
      canvas.height = Math.round(height * devicePixelRatio);
      this.gl.viewport(0, 0, canvas.width, canvas.height);

      this.gl.uniform2fv(this.uniforms.u_focal, new Float32Array([this.camera.fx, this.camera.fy]));
      this.gl.uniform2fv(this.uniforms.u_viewport, new Float32Array([width, height]));

      this.projectionMatrix = this.getProjectionMatrix(
        this.camera.fx, this.camera.fy, width, height
      );
      this.gl.uniformMatrix4fv(this.uniforms.u_projection, false, this.projectionMatrix);
    },

    onMouseDown(e) {
      e.preventDefault();
      this.mouseState.down = true;
      this.mouseState.startX = e.clientX;
      this.mouseState.startY = e.clientY;
    },

    onMouseMove(e) {
      e.preventDefault();
      if (!this.mouseState.down) return;

      const dx = (5 * (e.clientX - this.mouseState.startX)) / this.$refs.canvas.clientWidth;
      const dy = (5 * (e.clientY - this.mouseState.startY)) / this.$refs.canvas.clientHeight;

      let inv = this.invert4(this.viewMatrix);
      const d = 4;
      inv = this.translate4(inv, 0, 0, d);
      inv = this.rotate4(inv, dx, 0, 1, 0);
      inv = this.rotate4(inv, -dy, 1, 0, 0);
      inv = this.translate4(inv, 0, 0, -d);
      this.viewMatrix = this.invert4(inv);

      this.mouseState.startX = e.clientX;
      this.mouseState.startY = e.clientY;
    },

    onMouseUp(e) {
      e.preventDefault();
      this.mouseState.down = false;
    },

    onWheel(e) {
      e.preventDefault();
      let inv = this.invert4(this.viewMatrix);
      inv = this.translate4(inv, 0, 0, e.deltaY * 0.01);
      this.viewMatrix = this.invert4(inv);
    },

    //
    // UTILITY & CLEANUP
    //
    cleanupScene() {
        if(this.gl) {
            this.gl.clear(this.gl.COLOR_BUFFER_BIT);
        }
        this.vertexCount = 0;
    },
    cleanup() {
      window.removeEventListener('resize', this.handleResize);
      if (this.worker) {
        this.worker.terminate();
      }
      if (this.animationFrameId) {
        cancelAnimationFrame(this.animationFrameId);
      }
      const canvas = this.$refs.canvas;
      if (canvas) {
        canvas.removeEventListener('mousedown', this.onMouseDown);
        canvas.removeEventListener('mousemove', this.onMouseMove);
        canvas.removeEventListener('mouseup', this.onMouseUp);
        canvas.removeEventListener('mouseout', this.onMouseUp);
        canvas.removeEventListener('wheel', this.onWheel);
      }
    },

    //
    // MATRIX MATH HELPERS (from 3dgs-webgl)
    //
    getProjectionMatrix(fx, fy, width, height) {
      const znear = 0.2;
      const zfar = 200;
      return [
        (2 * fx) / width, 0, 0, 0,
        0, -(2 * fy) / height, 0, 0,
        0, 0, zfar / (zfar - znear), 1,
        0, 0, -(zfar * znear) / (zfar - znear), 0,
      ];
    },
    multiply4(a, b) {
      return [
        b[0] * a[0] + b[1] * a[4] + b[2] * a[8] + b[3] * a[12],
        b[0] * a[1] + b[1] * a[5] + b[2] * a[9] + b[3] * a[13],
        b[0] * a[2] + b[1] * a[6] + b[2] * a[10] + b[3] * a[14],
        b[0] * a[3] + b[1] * a[7] + b[2] * a[11] + b[3] * a[15],
        b[4] * a[0] + b[5] * a[4] + b[6] * a[8] + b[7] * a[12],
        b[4] * a[1] + b[5] * a[5] + b[6] * a[9] + b[7] * a[13],
        b[4] * a[2] + b[5] * a[6] + b[6] * a[10] + b[7] * a[14],
        b[4] * a[3] + b[5] * a[7] + b[6] * a[11] + b[7] * a[15],
        b[8] * a[0] + b[9] * a[4] + b[10] * a[8] + b[11] * a[12],
        b[8] * a[1] + b[9] * a[5] + b[10] * a[9] + b[11] * a[13],
        b[8] * a[2] + b[9] * a[6] + b[10] * a[10] + b[11] * a[14],
        b[8] * a[3] + b[9] * a[7] + b[10] * a[11] + b[11] * a[15],
        b[12] * a[0] + b[13] * a[4] + b[14] * a[8] + b[15] * a[12],
        b[12] * a[1] + b[13] * a[5] + b[14] * a[9] + b[15] * a[13],
        b[12] * a[2] + b[13] * a[6] + b[14] * a[10] + b[15] * a[14],
        b[12] * a[3] + b[13] * a[7] + b[14] * a[11] + b[15] * a[15],
      ];
    },
    invert4(a) {
      let b00 = a[0] * a[5] - a[1] * a[4];
      let b01 = a[0] * a[6] - a[2] * a[4];
      let b02 = a[0] * a[7] - a[3] * a[4];
      let b03 = a[1] * a[6] - a[2] * a[5];
      let b04 = a[1] * a[7] - a[3] * a[5];
      let b05 = a[2] * a[7] - a[3] * a[6];
      let b06 = a[8] * a[13] - a[9] * a[12];
      let b07 = a[8] * a[14] - a[10] * a[12];
      let b08 = a[8] * a[15] - a[11] * a[12];
      let b09 = a[9] * a[14] - a[10] * a[13];
      let b10 = a[9] * a[15] - a[11] * a[13];
      let b11 = a[10] * a[15] - a[11] * a[14];
      let det = b00 * b11 - b01 * b10 + b02 * b09 + b03 * b08 - b04 * b07 + b05 * b06;
      if (!det) return null;
      det = 1.0 / det;
      const out = [];
      out[0] = (a[5] * b11 - a[6] * b10 + a[7] * b09) * det;
      out[1] = (a[2] * b10 - a[1] * b11 - a[3] * b09) * det;
      out[2] = (a[13] * b05 - a[14] * b04 + a[15] * b03) * det;
      out[3] = (a[10] * b04 - a[9] * b05 - a[11] * b03) * det;
      out[4] = (a[6] * b08 - a[4] * b11 - a[7] * b07) * det;
      out[5] = (a[0] * b11 - a[2] * b08 + a[3] * b07) * det;
      out[6] = (a[14] * b02 - a[12] * b05 - a[15] * b01) * det;
      out[7] = (a[8] * b05 - a[10] * b02 + a[11] * b01) * det;
      out[8] = (a[4] * b10 - a[5] * b08 + a[7] * b06) * det;
      out[9] = (a[1] * b08 - a[0] * b10 - a[3] * b06) * det;
      out[10] = (a[12] * b04 - a[13] * b02 + a[15] * b00) * det;
      out[11] = (a[9] * b02 - a[8] * b04 - a[11] * b00) * det;
      out[12] = (a[5] * b07 - a[4] * b09 - a[6] * b06) * det;
      out[13] = (a[0] * b09 - a[1] * b07 + a[2] * b06) * det;
      out[14] = (a[13] * b01 - a[12] * b03 - a[14] * b00) * det;
      out[15] = (a[8] * b03 - a[9] * b01 + a[10] * b00) * det;
      return out;
    },
    rotate4(a, rad, x, y, z) {
        let len = Math.hypot(x, y, z);
        x /= len; y /= len; z /= len;
        let s = Math.sin(rad);
        let c = Math.cos(rad);
        let t = 1 - c;
        let b00 = x * x * t + c, b01 = y * x * t + z * s, b02 = z * x * t - y * s;
        let b10 = x * y * t - z * s, b11 = y * y * t + c, b12 = z * y * t + x * s;
        let b20 = x * z * t + y * s, b21 = y * z * t - x * s, b22 = z * z * t + c;
        const out = [];
        out[0] = a[0] * b00 + a[4] * b01 + a[8] * b02;
        out[1] = a[1] * b00 + a[5] * b01 + a[9] * b02;
        out[2] = a[2] * b00 + a[6] * b01 + a[10] * b02;
        out[3] = a[3] * b00 + a[7] * b01 + a[11] * b02;
        out[4] = a[0] * b10 + a[4] * b11 + a[8] * b12;
        out[5] = a[1] * b10 + a[5] * b11 + a[9] * b12;
        out[6] = a[2] * b10 + a[6] * b11 + a[10] * b12;
        out[7] = a[3] * b10 + a[7] * b11 + a[11] * b12;
        out[8] = a[0] * b20 + a[4] * b21 + a[8] * b22;
        out[9] = a[1] * b20 + a[5] * b21 + a[9] * b22;
        out[10] = a[2] * b20 + a[6] * b21 + a[10] * b22;
        out[11] = a[3] * b20 + a[7] * b21 + a[11] * b22;
        out[12] = a[12];
        out[13] = a[13];
        out[14] = a[14];
        out[15] = a[15];
        return out;
    },
    translate4(a, x, y, z) {
      const out = [...a];
      out[12] = a[0] * x + a[4] * y + a[8] * z + a[12];
      out[13] = a[1] * x + a[5] * y + a[9] * z + a[13];
      out[14] = a[2] * x + a[6] * y + a[10] * z + a[14];
      out[15] = a[3] * x + a[7] * y + a[11] * z + a[15];
      return out;
    },
  },
};
</script>

<style scoped>
.splat-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background-color: #000;
}

.splat-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.spinner-container, .message-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  pointer-events: none;
}
.message-container p {
  color: white;
  font-size: 1.2rem;
  background-color: rgba(0, 0, 0, 0.5);
  padding: 10px 20px;
  border-radius: 8px;
}

.info-overlay {
    position: absolute;
    top: 10px;
    right: 15px;
    z-index: 100;
    color: white;
    text-shadow: 0 0 3px black;
    font-family: sans-serif;
    font-size: small;
}


/* Spinner styles from 3dgs-webgl/index.html */
.cube-wrapper {
  transform-style: preserve-3d;
}

.cube {
  transform-style: preserve-3d;
  transform: rotateX(45deg) rotateZ(45deg);
  animation: rotation 2s infinite;
}

.cube-faces {
  transform-style: preserve-3d;
  height: 80px;
  width: 80px;
  position: relative;
  transform-origin: 0 0;
  transform: translateX(0) translateY(0) translateZ(-40px);
}

.cube-face {
  position: absolute;
  inset: 0;
  background: #007bff;
  border: solid 1px #ffffff;
}
.cube-face.top { transform: translateZ(80px); }
.cube-face.front { transform-origin: 0 50%; transform: rotateY(-90deg); }
.cube-face.back { transform-origin: 0 50%; transform: rotateY(-90deg) translateZ(-80px); }
.cube-face.right { transform-origin: 50% 0; transform: rotateX(-90deg) translateY(-80px); }
.cube-face.left { transform-origin: 50% 0; transform: rotateX(-90deg) translateY(-80px) translateZ(80px); }

@keyframes rotation {
  0% {
    transform: rotateX(45deg) rotateY(0) rotateZ(45deg);
    animation-timing-function: cubic-bezier(0.17, 0.84, 0.44, 1);
  }
  50% {
    transform: rotateX(45deg) rotateY(0) rotateZ(225deg);
    animation-timing-function: cubic-bezier(0.76, 0.05, 0.86, 0.06);
  }
  100% {
    transform: rotateX(45deg) rotateY(0) rotateZ(405deg);
    animation-timing-function: cubic-bezier(0.17, 0.84, 0.44, 1);
  }
}
</style> 