(function () {
  var LIBRARY = JSON.parse(document.getElementById('payload').textContent);
  var ids = Object.keys(LIBRARY);

  var canvas = document.getElementById('stage');
  var gl = canvas.getContext('webgl', { antialias: true, alpha: true });
  if (!gl) {
    document.getElementById('fallback').hidden = false;
    return;
  }

  // --- shaders -------------------------------------------------------------
  // Lambert plus a rim term. Enough to read a body's form without pretending
  // to be a render engine.
  var VERTEX = [
    'attribute vec3 position;',
    'attribute vec3 normal;',
    'uniform mat4 modelView;',
    'uniform mat4 projection;',
    'uniform mat3 normalMatrix;',
    'varying vec3 vNormal;',
    'varying vec3 vEye;',
    'void main() {',
    '  vec4 eye = modelView * vec4(position, 1.0);',
    '  vNormal = normalize(normalMatrix * normal);',
    '  vEye = -normalize(eye.xyz);',
    '  gl_Position = projection * eye;',
    '}'
  ].join('\n');

  var FRAGMENT = [
    'precision mediump float;',
    'varying vec3 vNormal;',
    'varying vec3 vEye;',
    'uniform vec3 baseColour;',
    'uniform vec3 rimColour;',
    'void main() {',
    '  vec3 n = normalize(vNormal);',
    '  vec3 key = normalize(vec3(0.4, 0.8, 0.6));',
    '  vec3 fill = normalize(vec3(-0.6, 0.2, 0.3));',
    '  float lit = max(dot(n, key), 0.0) * 0.78 + max(dot(n, fill), 0.0) * 0.22;',
    '  float rim = pow(1.0 - max(dot(n, normalize(vEye)), 0.0), 2.4);',
    '  vec3 colour = baseColour * (0.30 + 0.70 * lit) + rimColour * rim * 0.55;',
    '  gl_FragColor = vec4(colour, 1.0);',
    '}'
  ].join('\n');

  function compile(type, source) {
    var shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      throw new Error(gl.getShaderInfoLog(shader));
    }
    return shader;
  }

  var program = gl.createProgram();
  gl.attachShader(program, compile(gl.VERTEX_SHADER, VERTEX));
  gl.attachShader(program, compile(gl.FRAGMENT_SHADER, FRAGMENT));
  gl.linkProgram(program);
  gl.useProgram(program);

  var attributes = {
    position: gl.getAttribLocation(program, 'position'),
    normal: gl.getAttribLocation(program, 'normal')
  };
  var uniforms = {
    modelView: gl.getUniformLocation(program, 'modelView'),
    projection: gl.getUniformLocation(program, 'projection'),
    normalMatrix: gl.getUniformLocation(program, 'normalMatrix'),
    baseColour: gl.getUniformLocation(program, 'baseColour'),
    rimColour: gl.getUniformLocation(program, 'rimColour')
  };

  // A second, flat program for the skeleton overlay. Lines want no lighting.
  var LINE_VERTEX = [
    'attribute vec3 position;',
    'uniform mat4 modelView;',
    'uniform mat4 projection;',
    'void main() { gl_Position = projection * modelView * vec4(position, 1.0); }'
  ].join('\n');
  var LINE_FRAGMENT = [
    'precision mediump float;',
    'uniform vec3 lineColour;',
    'void main() { gl_FragColor = vec4(lineColour, 1.0); }'
  ].join('\n');

  var lineProgram = gl.createProgram();
  gl.attachShader(lineProgram, compile(gl.VERTEX_SHADER, LINE_VERTEX));
  gl.attachShader(lineProgram, compile(gl.FRAGMENT_SHADER, LINE_FRAGMENT));
  gl.linkProgram(lineProgram);
  var lineAttribute = gl.getAttribLocation(lineProgram, 'position');
  var lineUniforms = {
    modelView: gl.getUniformLocation(lineProgram, 'modelView'),
    projection: gl.getUniformLocation(lineProgram, 'projection'),
    lineColour: gl.getUniformLocation(lineProgram, 'lineColour')
  };
  var lineBuffer = gl.createBuffer();

  // A ball. Built once as a unit sphere, then moved and scaled per frame.
  function unitSphere(rings, segments) {
    var verts = [], index = [];
    for (var y = 0; y <= rings; y++) {
      var phi = Math.PI * y / rings;
      for (var x = 0; x <= segments; x++) {
        var theta = 2 * Math.PI * x / segments;
        verts.push(
          Math.sin(phi) * Math.cos(theta),
          Math.cos(phi),
          Math.sin(phi) * Math.sin(theta)
        );
      }
    }
    for (var ry = 0; ry < rings; ry++) {
      for (var rx = 0; rx < segments; rx++) {
        var a = ry * (segments + 1) + rx;
        var b = a + segments + 1;
        index.push(a, b, a + 1, b, b + 1, a + 1);
      }
    }
    return { verts: new Float32Array(verts), index: new Uint16Array(index) };
  }
  var sphere = unitSphere(14, 20);
  var ballPositions = new Float32Array(sphere.verts.length);
  var ballBuffer = gl.createBuffer();
  var ballNormalBuffer = gl.createBuffer();
  var ballIndexBuffer = gl.createBuffer();
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ballIndexBuffer);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, sphere.index, gl.STATIC_DRAW);

  var positionBuffer = gl.createBuffer();
  var normalBuffer = gl.createBuffer();
  var indexBuffer = gl.createBuffer();

  gl.enable(gl.DEPTH_TEST);
  gl.enable(gl.CULL_FACE);
  gl.cullFace(gl.BACK);

  // --- small matrix helpers ------------------------------------------------
  function perspective(fovy, aspect, near, far) {
    var f = 1.0 / Math.tan(fovy / 2);
    return [
      f / aspect, 0, 0, 0,
      0, f, 0, 0,
      0, 0, (far + near) / (near - far), -1,
      0, 0, (2 * far * near) / (near - far), 0
    ];
  }

  function lookAt(eye, centre, up) {
    function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
    function norm(v) {
      var l = Math.hypot(v[0], v[1], v[2]) || 1;
      return [v[0] / l, v[1] / l, v[2] / l];
    }
    function cross(a, b) {
      return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0]
      ];
    }
    function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
    var z = norm(sub(eye, centre));
    var x = norm(cross(up, z));
    var y = cross(z, x);
    return [
      x[0], y[0], z[0], 0,
      x[1], y[1], z[1], 0,
      x[2], y[2], z[2], 0,
      -dot(x, eye), -dot(y, eye), -dot(z, eye), 1
    ];
  }

  function normalFrom(modelView) {
    // Rotation only, so the upper 3x3 is its own normal matrix here.
    return [
      modelView[0], modelView[1], modelView[2],
      modelView[4], modelView[5], modelView[6],
      modelView[8], modelView[9], modelView[10]
    ];
  }

  // --- state ---------------------------------------------------------------
  var data = null;
  var faces = null;
  var positions = null;
  var normals = null;
  var frameIndex = 0;
  var skeleton = null;
  var showMesh = true;
  var showSkeleton = false;
  var ballCentre = null;
  var ballRadius = 11;
  var playing = true;
  var azimuth = 0.55;
  var elevation = 0.12;
  var distance = 1.0;
  var centre = [0, 0, 0];
  var span = 1;

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    playing = false;
  }

  function computeNormals(vertices, indices) {
    var out = new Float32Array(vertices.length);
    for (var i = 0; i < indices.length; i += 3) {
      var a = indices[i] * 3, b = indices[i + 1] * 3, c = indices[i + 2] * 3;
      var ux = vertices[b] - vertices[a];
      var uy = vertices[b + 1] - vertices[a + 1];
      var uz = vertices[b + 2] - vertices[a + 2];
      var vx = vertices[c] - vertices[a];
      var vy = vertices[c + 1] - vertices[a + 1];
      var vz = vertices[c + 2] - vertices[a + 2];
      var nx = uy * vz - uz * vy;
      var ny = uz * vx - ux * vz;
      var nz = ux * vy - uy * vx;
      out[a] += nx; out[a + 1] += ny; out[a + 2] += nz;
      out[b] += nx; out[b + 1] += ny; out[b + 2] += nz;
      out[c] += nx; out[c + 1] += ny; out[c + 2] += nz;
    }
    for (var v = 0; v < out.length; v += 3) {
      var l = Math.hypot(out[v], out[v + 1], out[v + 2]) || 1;
      out[v] /= l; out[v + 1] /= l; out[v + 2] /= l;
    }
    return out;
  }

  function readTheme() {
    var styles = getComputedStyle(document.body);
    function rgb(name, fallback) {
      var value = styles.getPropertyValue(name).trim();
      var match = value.match(/^#?([0-9a-f]{6})$/i);
      if (!match) { return fallback; }
      var n = parseInt(match[1], 16);
      return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
    }
    return {
      base: rgb('--body', [0.86, 0.42, 0.30]),
      rim: rgb('--panel', [0.21, 0.72, 0.65])
    };
  }

  function resize() {
    var ratio = Math.min(window.devicePixelRatio || 1, 2);
    // clientWidth is zero until the page has laid out, and a zero width canvas
    // draws nothing at all. Fall back to the parent, then to a sane default, so
    // the first paint is never blank.
    var width = canvas.clientWidth
      || (canvas.parentElement ? canvas.parentElement.clientWidth : 0)
      || 640;
    var height = canvas.clientHeight || 520;
    if (canvas.width !== Math.round(width * ratio)
        || canvas.height !== Math.round(height * ratio)) {
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
    }
    gl.viewport(0, 0, canvas.width, canvas.height);
    return canvas.width > 0 && canvas.height > 0;
  }

  function draw() {
    if (!data) { return; }
    if (!resize()) { return; }
    var theme = readTheme();
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    var radius = span * distance;
    var eye = [
      centre[0] + radius * Math.sin(azimuth) * Math.cos(elevation),
      centre[1] + radius * Math.sin(elevation),
      centre[2] + radius * Math.cos(azimuth) * Math.cos(elevation)
    ];
    var modelView = lookAt(eye, centre, [0, 1, 0]);
    var projection = perspective(
      0.72, canvas.width / Math.max(canvas.height, 1), span * 0.05, span * 12
    );

    if (showMesh) {
    gl.useProgram(program);
    gl.uniformMatrix4fv(uniforms.modelView, false, new Float32Array(modelView));
    gl.uniformMatrix4fv(uniforms.projection, false, new Float32Array(projection));
    gl.uniformMatrix3fv(
      uniforms.normalMatrix, false, new Float32Array(normalFrom(modelView))
    );
    gl.uniform3fv(uniforms.baseColour, new Float32Array(theme.base));
    gl.uniform3fv(uniforms.rimColour, new Float32Array(theme.rim));
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, positions, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(attributes.position);
    gl.vertexAttribPointer(attributes.position, 3, gl.FLOAT, false, 0, 0);

    gl.bindBuffer(gl.ARRAY_BUFFER, normalBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, normals, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(attributes.normal);
    gl.vertexAttribPointer(attributes.normal, 3, gl.FLOAT, false, 0, 0);

    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
    gl.drawElements(gl.TRIANGLES, faces.length, gl.UNSIGNED_SHORT, 0);
    }

    if (ballCentre) {
      for (var v = 0; v < sphere.verts.length; v += 3) {
        ballPositions[v] = ballCentre[0] + sphere.verts[v] * ballRadius;
        ballPositions[v + 1] = ballCentre[1] + sphere.verts[v + 1] * ballRadius;
        ballPositions[v + 2] = ballCentre[2] + sphere.verts[v + 2] * ballRadius;
      }
      gl.useProgram(program);
      gl.uniformMatrix4fv(uniforms.modelView, false, new Float32Array(modelView));
      gl.uniformMatrix4fv(uniforms.projection, false, new Float32Array(projection));
      gl.uniformMatrix3fv(
        uniforms.normalMatrix, false, new Float32Array(normalFrom(modelView))
      );
      gl.uniform3fv(uniforms.baseColour, new Float32Array(theme.rim));
      gl.uniform3fv(uniforms.rimColour, new Float32Array(theme.base));
      gl.bindBuffer(gl.ARRAY_BUFFER, ballBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, ballPositions, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(attributes.position);
      gl.vertexAttribPointer(attributes.position, 3, gl.FLOAT, false, 0, 0);
      // On a unit sphere the outward normal is the vertex itself.
      gl.bindBuffer(gl.ARRAY_BUFFER, ballNormalBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, sphere.verts, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(attributes.normal);
      gl.vertexAttribPointer(attributes.normal, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ballIndexBuffer);
      gl.drawElements(gl.TRIANGLES, sphere.index.length, gl.UNSIGNED_SHORT, 0);
    }

    if (showSkeleton && skeleton) {
      // Drawn without depth test so the bones stay visible through the body.
      gl.disable(gl.DEPTH_TEST);
      gl.useProgram(lineProgram);
      gl.uniformMatrix4fv(lineUniforms.modelView, false, new Float32Array(modelView));
      gl.uniformMatrix4fv(lineUniforms.projection, false, new Float32Array(projection));
      gl.uniform3fv(lineUniforms.lineColour, new Float32Array(theme.rim));
      gl.bindBuffer(gl.ARRAY_BUFFER, lineBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, skeleton, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(lineAttribute);
      gl.vertexAttribPointer(lineAttribute, 3, gl.FLOAT, false, 0, 0);
      gl.lineWidth(2);
      gl.drawArrays(gl.LINES, 0, skeleton.length / 3);
      gl.enable(gl.DEPTH_TEST);
    }
  }

  function showFrame(index) {
    frameIndex = index;
    positions = new Float32Array(data.frames[index]);
    skeleton = data.skeletons ? new Float32Array(data.skeletons[index]) : null;
    ballCentre = data.balls ? data.balls[index] : null;
    ballRadius = data.ballRadius || 11;
    normals = computeNormals(positions, faces);
    var fraction = index / Math.max(data.frames.length - 1, 1);
    document.getElementById('scrub').value = String(index);
    document.getElementById('frameNote').textContent =
      'frame ' + (index + 1) + ' of ' + data.frames.length;

    var names = Object.keys(data.phaseAnchors);
    var best = names[0], gap = Infinity;
    names.forEach(function (name) {
      var d = Math.abs(data.phaseAnchors[name] - fraction);
      if (d < gap) { gap = d; best = name; }
    });
    document.getElementById('phaseNow').textContent = best.replace(/_/g, ' ');

    var m = data.measurements[index];
    var rows = [
      ['left elbow', m.leftElbowFlexionDegrees],
      ['right elbow', m.rightElbowFlexionDegrees],
      ['left shoulder', m.leftShoulderElevationDegrees],
      ['left knee', m.leftKneeFlexionDegrees],
      ['trunk lean', m.trunkLeanDegrees]
    ];
    if (m.trunkTurnDegrees) { rows.push(['trunk turn', m.trunkTurnDegrees]); }
    if (m.footHeightGapCm !== undefined) {
      rows.push(['foot gap (cm)', m.footHeightGapCm]);
    }
    document.getElementById('readout').innerHTML = rows.map(function (row) {
      return '<div class="stat"><span>' + row[0] + '</span><b>'
        + row[1].toFixed(1) + '</b></div>';
    }).join('');
    draw();
  }

  function select(id) {
    data = LIBRARY[id];
    faces = new Uint16Array(data.faces);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, faces, gl.STATIC_DRAW);

    var lo = data.bounds.min, hi = data.bounds.max;
    centre = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2];
    span = Math.max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) * 1.35;

    document.getElementById('skill').textContent = data.skill;
    document.getElementById('source').textContent = data.source;
    document.getElementById('scrub').max = String(data.frames.length - 1);
    Array.prototype.forEach.call(
      document.getElementById('picker').children,
      function (button) {
        button.setAttribute(
          'aria-pressed', button.getAttribute('data-id') === id ? 'true' : 'false'
        );
      }
    );
    showFrame(0);
  }

  // --- orbit ---------------------------------------------------------------
  var dragging = false, lastX = 0, lastY = 0;

  function pointerDown(event) {
    dragging = true;
    lastX = event.clientX; lastY = event.clientY;
    canvas.setPointerCapture(event.pointerId);
  }
  function pointerMove(event) {
    if (!dragging) { return; }
    azimuth -= (event.clientX - lastX) * 0.01;
    elevation = Math.max(
      -1.2, Math.min(1.2, elevation + (event.clientY - lastY) * 0.008)
    );
    lastX = event.clientX; lastY = event.clientY;
    draw();
  }
  function pointerUp(event) {
    dragging = false;
    if (canvas.hasPointerCapture(event.pointerId)) {
      canvas.releasePointerCapture(event.pointerId);
    }
  }
  canvas.addEventListener('pointerdown', pointerDown);
  canvas.addEventListener('pointermove', pointerMove);
  canvas.addEventListener('pointerup', pointerUp);
  canvas.addEventListener('pointercancel', pointerUp);
  canvas.addEventListener('wheel', function (event) {
    event.preventDefault();
    distance = Math.max(0.45, Math.min(2.4, distance + event.deltaY * 0.0012));
    draw();
  }, { passive: false });

  // Keyboard orbit, so the view is reachable without a pointer.
  canvas.addEventListener('keydown', function (event) {
    var step = 0.12;
    if (event.key === 'ArrowLeft') { azimuth += step; }
    else if (event.key === 'ArrowRight') { azimuth -= step; }
    else if (event.key === 'ArrowUp') { elevation = Math.min(1.2, elevation + step); }
    else if (event.key === 'ArrowDown') { elevation = Math.max(-1.2, elevation - step); }
    else { return; }
    event.preventDefault();
    draw();
  });

  function syncToggles() {
    var mesh = document.getElementById('toggleMesh');
    var bones = document.getElementById('toggleSkeleton');
    mesh.setAttribute('aria-pressed', showMesh ? 'true' : 'false');
    bones.setAttribute('aria-pressed', showSkeleton ? 'true' : 'false');
  }

  document.getElementById('toggleMesh').addEventListener('click', function () {
    showMesh = !showMesh;
    // Never leave an empty canvas. Hiding the body turns the bones on.
    if (!showMesh && !showSkeleton) { showSkeleton = true; }
    syncToggles();
    draw();
  });
  document.getElementById('toggleSkeleton').addEventListener('click', function () {
    showSkeleton = !showSkeleton;
    if (!showMesh && !showSkeleton) { showMesh = true; }
    syncToggles();
    draw();
  });
  syncToggles();

  document.querySelectorAll('[data-view]').forEach(function (button) {
    button.addEventListener('click', function () {
      var name = button.getAttribute('data-view');
      azimuth = name === 'front' ? 0 : (name === 'side' ? Math.PI / 2 : Math.PI);
      elevation = 0.12;
      draw();
    });
  });

  ids.forEach(function (id) {
    var button = document.createElement('button');
    button.type = 'button';
    button.setAttribute('data-id', id);
    button.setAttribute('aria-pressed', 'false');
    button.textContent = LIBRARY[id].skill;
    button.addEventListener('click', function () { select(id); });
    document.getElementById('picker').appendChild(button);
  });

  var play = document.getElementById('play');
  play.textContent = playing ? 'Pause' : 'Play';
  play.addEventListener('click', function () {
    playing = !playing;
    play.textContent = playing ? 'Pause' : 'Play';
  });
  document.getElementById('scrub').addEventListener('input', function (event) {
    playing = false;
    play.textContent = 'Play';
    showFrame(Number(event.target.value));
  });

  window.addEventListener('resize', draw);
  // The canvas often gets its real width after the first paint. Redraw when it
  // does, rather than leaving a blank panel.
  if (window.ResizeObserver) {
    new ResizeObserver(function () { draw(); }).observe(canvas);
  }

  var last = 0;
  function tick(now) {
    if (playing && data && now - last > 1000 / (data.framesPerSecond || 24)) {
      last = now;
      showFrame((frameIndex + 1) % data.frames.length);
    }
    requestAnimationFrame(tick);
  }

  select(ids[0]);
  requestAnimationFrame(tick);
})();
