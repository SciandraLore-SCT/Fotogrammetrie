        let scene, camera, renderer, controls, currentModel;
        let loadedTexture = null;
        let autoRotate = true;
        let visualSettings = {
            brightness: 1.0,
            contrast: 1.0,
            saturation: 1.0,
            exposure: 1.0
        };

        // OrbitControls
        class OrbitControls {
            constructor(camera, domElement) {
                this.camera = camera;
                this.domElement = domElement;
                this.target = new THREE.Vector3();
                this.minDistance = 0.5;
                this.maxDistance = 1000;
                this.minPolarAngle = 0;
                this.maxPolarAngle = Math.PI;
                this.enableDamping = true;
                this.dampingFactor = 0.08;
                this.enablePan = true;
                this.autoRotate = true;
                this.autoRotateSpeed = 0.3;
                this.enabled = true;
                
                const scope = this;
                const STATE = { NONE: -1, ROTATE: 0, DOLLY: 1, PAN: 2 };
                
                let state = STATE.NONE;
                const spherical = new THREE.Spherical();
                const sphericalDelta = new THREE.Spherical();
                let scale = 1;
                const panOffset = new THREE.Vector3();
                let rotateStart = new THREE.Vector2();
                let rotateEnd = new THREE.Vector2();
                let rotateDelta = new THREE.Vector2();
                let panStart = new THREE.Vector2();
                let panEnd = new THREE.Vector2();
                let panDelta = new THREE.Vector2();
                
                function rotateLeft(angle) {
                    sphericalDelta.theta -= angle;
                }
                
                function rotateUp(angle) {
                    sphericalDelta.phi -= angle;
                }
                
                function panLeft(distance, objectMatrix) {
                    const v = new THREE.Vector3();
                    v.setFromMatrixColumn(objectMatrix, 0);
                    v.multiplyScalar(-distance);
                    panOffset.add(v);
                }
                
                function panUp(distance, objectMatrix) {
                    const v = new THREE.Vector3();
                    v.setFromMatrixColumn(objectMatrix, 1);
                    v.multiplyScalar(distance);
                    panOffset.add(v);
                }
                
                function pan(deltaX, deltaY) {
                    const offset = new THREE.Vector3();
                    const element = scope.domElement;
                    offset.copy(scope.camera.position).sub(scope.target);
                    let targetDistance = offset.length();
                    targetDistance *= Math.tan((scope.camera.fov / 2) * Math.PI / 180.0);
                    panLeft(2 * deltaX * targetDistance / element.clientHeight, scope.camera.matrix);
                    panUp(2 * deltaY * targetDistance / element.clientHeight, scope.camera.matrix);
                }
                
                function dollyIn(dollyScale) {
                    scale /= dollyScale;
                }
                
                function dollyOut(dollyScale) {
                    scale *= dollyScale;
                }
                
                function handleMouseDownRotate(event) {
                    rotateStart.set(event.clientX, event.clientY);
                }
                
                function handleMouseDownPan(event) {
                    panStart.set(event.clientX, event.clientY);
                }
                
                function handleMouseMoveRotate(event) {
                    rotateEnd.set(event.clientX, event.clientY);
                    rotateDelta.subVectors(rotateEnd, rotateStart).multiplyScalar(0.5);
                    const element = scope.domElement;
                    rotateLeft(2 * Math.PI * rotateDelta.x / element.clientHeight);
                    rotateUp(2 * Math.PI * rotateDelta.y / element.clientHeight);
                    rotateStart.copy(rotateEnd);
                    scope.update();
                }
                
                function handleMouseMovePan(event) {
                    panEnd.set(event.clientX, event.clientY);
                    panDelta.subVectors(panEnd, panStart).multiplyScalar(0.5);
                    pan(panDelta.x, panDelta.y);
                    panStart.copy(panEnd);
                    scope.update();
                }
                
                function handleMouseWheel(event) {
                    if (event.deltaY < 0) {
                        dollyOut(0.95);
                    } else if (event.deltaY > 0) {
                        dollyIn(0.95);
                    }
                    scope.update();
                }
                
                function onMouseDown(event) {
                    if (!scope.enabled) return;
                    event.preventDefault();
                    if (event.button === 0) {
                        state = STATE.ROTATE;
                        handleMouseDownRotate(event);
                    } else if (event.button === 2) {
                        state = STATE.PAN;
                        handleMouseDownPan(event);
                    }
                    document.addEventListener('mousemove', onMouseMove);
                    document.addEventListener('mouseup', onMouseUp);
                }
                
                function onMouseMove(event) {
                    if (!scope.enabled) return;
                    event.preventDefault();
                    if (state === STATE.ROTATE) {
                        handleMouseMoveRotate(event);
                    } else if (state === STATE.PAN) {
                        handleMouseMovePan(event);
                    }
                }
                
                function onMouseUp() {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                    state = STATE.NONE;
                }
                
                function onMouseWheel(event) {
                    if (!scope.enabled) return;
                    event.preventDefault();
                    handleMouseWheel(event);
                }
                
                this.domElement.addEventListener('mousedown', onMouseDown);
                this.domElement.addEventListener('wheel', onMouseWheel);
                this.domElement.addEventListener('contextmenu', (e) => e.preventDefault());
                
                this.update = function() {
                    const offset = new THREE.Vector3();
                    const quat = new THREE.Quaternion().setFromUnitVectors(
                        camera.up,
                        new THREE.Vector3(0, 1, 0)
                    );
                    const quatInverse = quat.clone().invert();
                    const lastPosition = new THREE.Vector3();
                    const lastQuaternion = new THREE.Quaternion();
                    
                    return function update() {
                        const position = scope.camera.position;
                        offset.copy(position).sub(scope.target);
                        offset.applyQuaternion(quat);
                        spherical.setFromVector3(offset);
                        
                        if (scope.autoRotate && state === STATE.NONE) {
                            rotateLeft(2 * Math.PI / 60 / 60 * scope.autoRotateSpeed);
                        }
                        
                        spherical.theta += sphericalDelta.theta;
                        spherical.phi += sphericalDelta.phi;
                        spherical.phi = Math.max(scope.minPolarAngle, Math.min(scope.maxPolarAngle, spherical.phi));
                        spherical.makeSafe();
                        spherical.radius *= scale;
                        spherical.radius = Math.max(scope.minDistance, Math.min(scope.maxDistance, spherical.radius));
                        
                        scope.target.add(panOffset);
                        offset.setFromSpherical(spherical);
                        offset.applyQuaternion(quatInverse);
                        position.copy(scope.target).add(offset);
                        scope.camera.lookAt(scope.target);
                        
                        if (scope.enableDamping) {
                            sphericalDelta.theta *= (1 - scope.dampingFactor);
                            sphericalDelta.phi *= (1 - scope.dampingFactor);
                            panOffset.multiplyScalar(1 - scope.dampingFactor);
                        } else {
                            sphericalDelta.set(0, 0, 0);
                            panOffset.set(0, 0, 0);
                        }
                        
                        scale = 1;
                        
                        if (lastPosition.distanceToSquared(scope.camera.position) > 0.000001 ||
                            8 * (1 - lastQuaternion.dot(scope.camera.quaternion)) > 0.000001) {
                            lastPosition.copy(scope.camera.position);
                            lastQuaternion.copy(scope.camera.quaternion);
                        }
                    };
                }();
            }
        }

        // OBJLoader ottimizzato per file grandi
        class OBJLoader {
            load(url, onLoad, onProgress, onError) {
                const xhr = new XMLHttpRequest();
                xhr.open('GET', url, true);
                xhr.responseType = 'text';
                
                xhr.onprogress = function(event) {
                    if (event.lengthComputable && onProgress) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        onProgress(percentComplete, event.loaded, event.total);
                    }
                };
                
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        try {
                            const object = new OBJLoader().parse(xhr.responseText);
                            onLoad(object);
                        } catch (e) {
                            if (onError) onError(e);
                        }
                    } else {
                        if (onError) onError(new Error('Failed to load'));
                    }
                };
                
                xhr.onerror = onError;
                xhr.send();
            }
            
            parse(text) {
                const vertices = [];
                const normals = [];
                const uvs = [];
                const faces = [];
                
                const lines = text.split('\n');
                const totalLines = lines.length;
                let processedLines = 0;
                
                lines.forEach(line => {
                    processedLines++;
                    if (processedLines % 10000 === 0) {
                        updateLoadingDetails(`Parsing geometria: ${((processedLines/totalLines)*100).toFixed(0)}%`);
                    }
                    
                    line = line.trim();
                    if (line.startsWith('v ')) {
                        const parts = line.split(/\s+/);
                        vertices.push(
                            parseFloat(parts[1]),
                            parseFloat(parts[2]),
                            parseFloat(parts[3])
                        );
                    } else if (line.startsWith('vn ')) {
                        const parts = line.split(/\s+/);
                        normals.push(
                            parseFloat(parts[1]),
                            parseFloat(parts[2]),
                            parseFloat(parts[3])
                        );
                    } else if (line.startsWith('vt ')) {
                        const parts = line.split(/\s+/);
                        uvs.push(
                            parseFloat(parts[1]),
                            1.0 - parseFloat(parts[2])
                        );
                    } else if (line.startsWith('f ')) {
                        const parts = line.substring(2).trim().split(/\s+/);
                        parts.forEach(part => {
                            faces.push(part);
                        });
                    }
                });
                
                updateLoadingDetails('Costruzione mesh...');
                
                const geometry = new THREE.BufferGeometry();
                const positions = [];
                const normalsArray = [];
                const uvsArray = [];
                
                for (let i = 0; i < faces.length; i += 3) {
                    if (i % 30000 === 0) {
                        updateLoadingDetails(`Costruzione mesh: ${((i/faces.length)*100).toFixed(0)}%`);
                    }
                    
                    for (let j = 0; j < 3; j++) {
                        const indices = faces[i + j].split('/');
                        const vIdx = (parseInt(indices[0]) - 1) * 3;
                        
                        if (vIdx >= 0 && vIdx < vertices.length) {
                            positions.push(vertices[vIdx], vertices[vIdx + 1], vertices[vIdx + 2]);
                        }
                        
                        if (indices[1] && indices[1] !== '') {
                            const uvIdx = (parseInt(indices[1]) - 1) * 2;
                            if (uvIdx >= 0 && uvIdx < uvs.length) {
                                uvsArray.push(uvs[uvIdx], uvs[uvIdx + 1]);
                            }
                        }
                        
                        if (indices[2] && indices[2] !== '') {
                            const nIdx = (parseInt(indices[2]) - 1) * 3;
                            if (nIdx >= 0 && nIdx < normals.length) {
                                normalsArray.push(normals[nIdx], normals[nIdx + 1], normals[nIdx + 2]);
                            }
                        }
                    }
                }
                
                geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
                
                if (normalsArray.length > 0) {
                    geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normalsArray, 3));
                } else {
                    updateLoadingDetails('Calcolo normali...');
                    geometry.computeVertexNormals();
                }
                
                if (uvsArray.length > 0) {
                    geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvsArray, 2));
                }
                
                const material = new THREE.MeshStandardMaterial({
                    color: 0xcccccc,
                    side: THREE.DoubleSide,
                    flatShading: false,
                    roughness: 0.7,
                    metalness: 0.1
                });
                
                const mesh = new THREE.Mesh(geometry, material);
                const group = new THREE.Group();
                group.add(mesh);
                
                return group;
            }
        }

        function init() {
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x2a2a2a);

            camera = new THREE.PerspectiveCamera(
                45,
                window.innerWidth / window.innerHeight,
                0.1,
                10000
            );
            camera.position.set(5, 5, 5);

            const container = document.getElementById('viewer-container');
            renderer = new THREE.WebGLRenderer({ 
                antialias: true, 
                preserveDrawingBuffer: true,
                powerPreference: "high-performance"
            });
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            renderer.shadowMap.enabled = true;
            renderer.outputEncoding = THREE.sRGBEncoding;
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            renderer.toneMappingExposure = 1.0;
            container.appendChild(renderer.domElement);

            controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.08;
            controls.minDistance = 0.5;
            controls.maxDistance = 1000;
            controls.maxPolarAngle = Math.PI;
            controls.minPolarAngle = 0;
            controls.enablePan = true;
            controls.autoRotate = true;
            controls.autoRotateSpeed = 0.3;

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
            scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(10, 10, 10);
            directionalLight.castShadow = true;
            scene.add(directionalLight);

            const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.5);
            directionalLight2.position.set(-10, -10, -10);
            scene.add(directionalLight2);

            const directionalLight3 = new THREE.DirectionalLight(0xffffff, 0.3);
            directionalLight3.position.set(0, -10, 0);
            scene.add(directionalLight3);

            const gridHelper = new THREE.GridHelper(20, 20, 0x555555, 0x333333);
            scene.add(gridHelper);

            window.addEventListener('resize', onWindowResize, false);
            animate();
            showStatus('Pronto! Carica un modello OBJ', 'success');
            
            // Monitor memoria
            setInterval(updateMemoryUsage, 2000);
        }

        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }

        function onWindowResize() {
            const container = document.getElementById('viewer-container');
            camera.aspect = container.clientWidth / container.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(container.clientWidth, container.clientHeight);
        }

        function clearModel() {
            if (currentModel) {
                scene.remove(currentModel);
                currentModel.traverse((child) => {
                    if (child.geometry) child.geometry.dispose();
                    if (child.material) {
                        if (Array.isArray(child.material)) {
                            child.material.forEach(mat => mat.dispose());
                        } else {
                            child.material.dispose();
                        }
                    }
                });
                currentModel = null;
            }
        }

        function centerModel(model) {
            const box = new THREE.Box3().setFromObject(model);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());

            model.position.sub(center);

            const maxDim = Math.max(size.x, size.y, size.z);
            const fov = camera.fov * (Math.PI / 180);
            const cameraDistance = maxDim / (2 * Math.tan(fov / 2)) * 1.5;

            camera.position.set(cameraDistance, cameraDistance * 0.7, cameraDistance);
            camera.lookAt(0, 0, 0);
            controls.target.set(0, 0, 0);
            controls.update();

            showStatus('Modello caricato con successo!', 'success');
            updateModelInfo(model, size);
        }

        function updateModelInfo(model, size) {
            let triangles = 0;
            let materials = 0;
            
            model.traverse((child) => {
                if (child.isMesh) {
                    if (child.geometry) {
                        const positionAttribute = child.geometry.getAttribute('position');
                        if (positionAttribute) {
                            triangles += positionAttribute.count / 3;
                        }
                    }
                    if (child.material) {
                        materials++;
                    }
                }
            });

            document.getElementById('modelTriangles').textContent = Math.floor(triangles).toLocaleString();
            document.getElementById('modelSize').textContent = 
                `${size.x.toFixed(1)} × ${size.y.toFixed(1)} × ${size.z.toFixed(1)}`;
            document.getElementById('modelInfo').style.display = 'block';
        }

        function updateMemoryUsage() {
            if (performance.memory) {
                const usedMB = (performance.memory.usedJSHeapSize / 1048576).toFixed(0);
                document.getElementById('memoryUsage').textContent = usedMB + ' MB';
            }
        }

        function showStatus(message, type = 'info') {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
            status.style.display = 'block';
            
            if (type === 'success') {
                setTimeout(() => {
                    status.style.display = 'none';
                }, 3000);
            }
        }

        function showLoading(show) {
            document.getElementById('loadingOverlay').classList.toggle('show', show);
        }

        function updateLoadingProgress(percent) {
            const fill = document.getElementById('progressFill');
            fill.style.width = percent + '%';
            fill.textContent = Math.round(percent) + '%';
        }

        function updateLoadingText(text) {
            document.getElementById('loadingText').textContent = text;
        }

        function updateLoadingDetails(text) {
            document.getElementById('loadingDetails').textContent = text;
        }

        window.loadOBJ = function(objFile, mtlFile = null, textureFile = null) {
            showLoading(true);
            updateLoadingText('Caricamento OBJ...');
            updateLoadingDetails('Lettura file (' + formatBytes(objFile.size) + ')');
            updateLoadingProgress(0);
            
            clearModel();

            const objUrl = URL.createObjectURL(objFile);
            const objLoader = new OBJLoader();
            
            document.getElementById('fileSize').textContent = formatBytes(objFile.size);
            
            objLoader.load(
                objUrl, 
                (object) => {
                    updateLoadingText('Finalizzazione...');
                    updateLoadingProgress(95);
                    
                    currentModel = object;
                    
                    if (textureFile) {
                        loadAndApplyTexture(textureFile);
                    } else if (loadedTexture) {
                        applyTextureToModel(currentModel, loadedTexture);
                    }
                    
                    scene.add(currentModel);
                    centerModel(currentModel);
                    
                    updateLoadingProgress(100);
                    setTimeout(() => {
                        showLoading(false);
                        URL.revokeObjectURL(objUrl);
                    }, 500);
                }, 
                (percent, loaded, total) => {
                    updateLoadingProgress(percent * 0.5);
                    updateLoadingDetails(`Caricamento: ${formatBytes(loaded)} / ${formatBytes(total)}`);
                }, 
                (error) => {
                    console.error('Errore caricamento OBJ:', error);
                    showLoading(false);
                    showStatus('Errore nel caricamento del file OBJ', 'error');
                }
            );
        };

        window.loadAndApplyTexture = function(file) {
            const isModelLoaded = currentModel !== null;
            
            if (!isModelLoaded) {
                showLoading(true);
                updateLoadingText('Caricamento texture...');
                updateLoadingDetails('Attendere...');
            }
            
            const textureLoader = new THREE.TextureLoader();
            const url = URL.createObjectURL(file);

            textureLoader.load(url, (texture) => {
                texture.encoding = THREE.sRGBEncoding;
                texture.wrapS = THREE.RepeatWrapping;
                texture.wrapT = THREE.RepeatWrapping;
                texture.minFilter = THREE.LinearMipmapLinearFilter;
                texture.magFilter = THREE.LinearFilter;
                texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
                texture.flipY = false;
                
                loadedTexture = texture;
                
                if (currentModel) {
                    applyTextureToModel(currentModel, texture);
                    showStatus('Texture applicata con successo!', 'success');
                } else {
                    showStatus('Texture caricata. Ora carica il modello OBJ.', 'success');
                }
                
                if (!isModelLoaded) {
                    showLoading(false);
                }
                
                URL.revokeObjectURL(url);
            }, null, (error) => {
                console.error('Errore caricamento texture:', error);
                showLoading(false);
                showStatus('Errore nel caricamento della texture', 'error');
            });
        };

        function applyTextureToModel(model, texture) {
            model.traverse((child) => {
                if (child.isMesh) {
                    const hasUVs = child.geometry.getAttribute('uv') !== undefined;
                    
                    if (hasUVs) {
                        if (child.material) {
                            if (Array.isArray(child.material)) {
                                child.material.forEach(mat => {
                                    mat.map = texture;
                                    mat.needsUpdate = true;
                                });
                            } else {
                                child.material.map = texture;
                                child.material.needsUpdate = true;
                            }
                        }
                    }
                }
            });
            
            applyVisualSettings();
            renderer.render(scene, camera);
        }

        function applyVisualSettings() {
            if (!currentModel) return;
            
            renderer.toneMappingExposure = visualSettings.exposure;
            
            currentModel.traverse((child) => {
                if (child.isMesh && child.material) {
                    const materials = Array.isArray(child.material) ? child.material : [child.material];
                    
                    materials.forEach(mat => {
                        if (mat.map) {
                            // Simula contrasto/luminosità/saturazione tramite shader uniforms
                            if (!mat.userData.originalColor) {
                                mat.userData.originalColor = mat.color.clone();
                            }
                            
                            const brightness = visualSettings.brightness;
                            const r = mat.userData.originalColor.r * brightness;
                            const g = mat.userData.originalColor.g * brightness;
                            const b = mat.userData.originalColor.b * brightness;
                            
                            mat.color.setRGB(
                                Math.min(r, 1),
                                Math.min(g, 1),
                                Math.min(b, 1)
                            );
                        }
                        mat.needsUpdate = true;
                    });
                }
            });
        }

        window.resetCamera = function() {
            if (currentModel) {
                centerModel(currentModel);
            } else {
                camera.position.set(5, 5, 5);
                controls.target.set(0, 0, 0);
                controls.update();
            }
        };

        window.toggleRotation = function() {
            autoRotate = !autoRotate;
            controls.autoRotate = autoRotate;
            const btn = event.target;
            btn.textContent = autoRotate ? '⏸ Pausa Rotazione' : '▶ Riprendi Rotazione';
        };

        window.toggleWireframe = function() {
            if (!currentModel) return;
            
            currentModel.traverse((child) => {
                if (child.isMesh && child.material) {
                    if (Array.isArray(child.material)) {
                        child.material.forEach(mat => {
                            mat.wireframe = !mat.wireframe;
                        });
                    } else {
                        child.material.wireframe = !child.material.wireframe;
                    }
                }
            });
        };

        window.changeBackground = function(color) {
            scene.background = new THREE.Color(color);
        };

        window.takeScreenshot = function() {
            renderer.render(scene, camera);
            const dataURL = renderer.domElement.toDataURL('image/png');
            const link = document.createElement('a');
            link.download = 'fotogrammetria_screenshot.png';
            link.href = dataURL;
            link.click();
            showStatus('Screenshot salvato!', 'success');
        };

        window.resetVisuals = function() {
            visualSettings.brightness = 1.0;
            visualSettings.contrast = 1.0;
            visualSettings.saturation = 1.0;
            visualSettings.exposure = 1.0;
            
            document.getElementById('brightnessSlider').value = 1.0;
            document.getElementById('contrastSlider').value = 1.0;
            document.getElementById('saturationSlider').value = 1.0;
            document.getElementById('exposureSlider').value = 1.0;
            
            document.getElementById('brightnessValue').textContent = '1.0';
            document.getElementById('contrastValue').textContent = '1.0';
            document.getElementById('saturationValue').textContent = '1.0';
            document.getElementById('exposureValue').textContent = '1.0';
            
            applyVisualSettings();
        };

        function formatBytes(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        window.addEventListener('DOMContentLoaded', init);

        document.addEventListener('DOMContentLoaded', function() {
            // File handlers
            document.getElementById('objFile').addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const mtlFile = document.getElementById('mtlFile').files[0];
                    const textureFile = document.getElementById('textureFile').files[0];
                    loadOBJ(file, mtlFile, textureFile);
                    document.getElementById('objLabel').textContent = '✅ ' + file.name;
                    document.getElementById('objLabel').classList.add('has-file');
                }
            });

            document.getElementById('mtlFile').addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    document.getElementById('mtlLabel').textContent = '✅ ' + file.name;
                    document.getElementById('mtlLabel').classList.add('has-file');
                }
            });

            document.getElementById('textureFile').addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    loadAndApplyTexture(file);
                    document.getElementById('textureLabel').textContent = '✅ ' + file.name;
                    document.getElementById('textureLabel').classList.add('has-file');
                }
            });

            // Visual controls
            document.getElementById('brightnessSlider').addEventListener('input', function(e) {
                visualSettings.brightness = parseFloat(e.target.value);
                document.getElementById('brightnessValue').textContent = e.target.value;
                applyVisualSettings();
            });

            document.getElementById('contrastSlider').addEventListener('input', function(e) {
                visualSettings.contrast = parseFloat(e.target.value);
                document.getElementById('contrastValue').textContent = e.target.value;
                applyVisualSettings();
            });

            document.getElementById('saturationSlider').addEventListener('input', function(e) {
                visualSettings.saturation = parseFloat(e.target.value);
                document.getElementById('saturationValue').textContent = e.target.value;
                applyVisualSettings();
            });

            document.getElementById('exposureSlider').addEventListener('input', function(e) {
                visualSettings.exposure = parseFloat(e.target.value);
                document.getElementById('exposureValue').textContent = e.target.value;
                applyVisualSettings();
            });

            // Drag & Drop
            const container = document.getElementById('viewer-container');
            
            container.addEventListener('dragover', (e) => {
                e.preventDefault();
                container.style.opacity = '0.7';
            });

            container.addEventListener('dragleave', () => {
                container.style.opacity = '1';
            });

            container.addEventListener('drop', (e) => {
                e.preventDefault();
                container.style.opacity = '1';
                
                const files = Array.from(e.dataTransfer.files);
                const objFile = files.find(f => f.name.toLowerCase().endsWith('.obj'));
                const mtlFile = files.find(f => f.name.toLowerCase().endsWith('.mtl'));
                const textureFile = files.find(f => {
                    const name = f.name.toLowerCase();
                    return name.endsWith('.jpg') || name.endsWith('.jpeg') || 
                           name.endsWith('.png') || name.endsWith('.bmp') ||
                           name.endsWith('.tga') || name.endsWith('.tiff') ||
                           name.endsWith('.webp');
                });
                
                if (objFile) {
                    loadOBJ(objFile, mtlFile, textureFile);
                    document.getElementById('objLabel').textContent = '✅ ' + objFile.name;
                    document.getElementById('objLabel').classList.add('has-file');
                }
                
                if (textureFile && !objFile) {
                    loadAndApplyTexture(textureFile);
                    document.getElementById('textureLabel').textContent = '✅ ' + textureFile.name;
                    document.getElementById('textureLabel').classList.add('has-file');
                }
                
                if (mtlFile) {
                    document.getElementById('mtlLabel').textContent = '✅ ' + mtlFile.name;
                    document.getElementById('mtlLabel').classList.add('has-file');
                }
            });
        });
