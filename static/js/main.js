document.addEventListener('DOMContentLoaded', () => {
    // --- Globals & Element Selectors ---
    const mainApp = document.getElementById('main-app');
    const tabs = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    const postsContainer = document.getElementById('posts-container');
    const refreshButton = document.getElementById('refresh-posts');
    const queueLoader = document.getElementById('queue-loader');
    const editorContainer = document.getElementById('editor-view-container');
    const historyContainer = document.getElementById('history-container');
    const clearHistoryButton = document.getElementById('clear-history');
    
    // Auth selectors
    const authModal = document.getElementById('auth-modal');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const showRegisterLink = document.getElementById('show-register');
    const showLoginLink = document.getElementById('show-login');
    const authError = document.getElementById('auth-error');
    const authTitle = document.getElementById('auth-title');
    const authSubtitle = document.getElementById('auth-subtitle');
    const userEmailSpan = document.getElementById('user-email');
    const logoutBtn = document.getElementById('logout-btn');

    // Image viewer selectors
    const imageViewer = document.getElementById('image-viewer');
    const viewerImage = document.getElementById('viewer-image');
    const closeImageViewerButton = document.getElementById('image-viewer-close');

    // Upload selectors
    const uploadInput = document.getElementById('image-upload-input');
    const uploadButton = document.getElementById('upload-image-btn');
    const uploadStatus = document.getElementById('upload-status');
    
    const navDashboardBtn = document.getElementById('nav-dashboard-btn');

    const API_BASE_URL = window.location.origin;
    const HISTORY_KEY = 'boographHistory';
    const TOKEN_KEY = 'boographToken';

    // --- Authentication ---
    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function setToken(token) {
        localStorage.setItem(TOKEN_KEY, token);
    }

    function removeToken() {
        localStorage.removeItem(TOKEN_KEY);
    }

    function checkAuth() {
        const token = getToken();
        if (token) {
            mainApp.classList.remove('opacity-0');
            authModal.classList.add('hidden');
            authModal.classList.remove('flex');
            
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                userEmailSpan.textContent = payload.sub;
                userEmailSpan.classList.remove('hidden');
                logoutBtn.classList.remove('hidden');
            } catch (e) {
                console.error("Failed to decode token:", e);
                removeToken();
                checkAuth();
                return;
            }

            fetchPosts(); // Load initial data for logged-in user
        } else {
            mainApp.classList.add('opacity-0');
            authModal.classList.remove('hidden');
            authModal.classList.add('flex');
            userEmailSpan.classList.add('hidden');
            logoutBtn.classList.add('hidden');
        }
    }

    async function apiFetch(url, options = {}) {
        const token = getToken();
        const headers = options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const finalOptions = { ...options, headers };
        const response = await fetch(url, finalOptions);
        
        if (response.status === 401) {
            removeToken();
            checkAuth();
            throw new Error('Session expired. Please log in again.');
        }

        return response;
    }


    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        authError.textContent = '';
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        try {
            const response = await fetch(`${API_BASE_URL}/api/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Login failed');
            setToken(data.access_token);
            checkAuth();
        } catch (error) {
            authError.textContent = error.message;
        }
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        authError.textContent = '';
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        const referralCode = document.getElementById('register-referral').value; // Get referral code
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // Add referral code to the request body
                body: JSON.stringify({ email, password, referralCode }) 
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Registration failed');
            
            showLoginForm();
            authError.textContent = 'Registration successful! Please log in.';
            authError.classList.remove('text-red-500');
            authError.classList.add('text-green-500');

        } catch (error) {
            authError.textContent = error.message;
            authError.classList.add('text-red-500');
            authError.classList.remove('text-green-500');
        }
    });

    logoutBtn.addEventListener('click', () => {
        removeToken();
        postsContainer.innerHTML = '';
        editorContainer.innerHTML = `<div class="text-center py-20 border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg"><h3 class="text-xl font-semibold text-gray-500">Logged Out</h3><p class="text-gray-400 mt-2">Please log in to continue.</p></div>`;
        historyContainer.innerHTML = `<div class="text-center py-20 border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg"><p class="text-gray-500">No history yet.</p></div>`;
        checkAuth();
    });

    function showRegisterForm() {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        authTitle.textContent = 'Create an Account';
        authSubtitle.textContent = 'Get started with your free account.';
        authError.textContent = '';
    }

    function showLoginForm() {
        registerForm.classList.add('hidden');
        loginForm.classList.remove('hidden');
        authTitle.textContent = 'Welcome Back';
        authSubtitle.textContent = 'Please sign in to continue.';
        authError.textContent = '';
    }

    showRegisterLink.addEventListener('click', (e) => { e.preventDefault(); showRegisterForm(); });
    showLoginLink.addEventListener('click', (e) => { e.preventDefault(); showLoginForm(); });


    // --- Tab Functionality ---
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.tab;
            activateTab(targetTab);
        });
    });

    if (navDashboardBtn) {
        navDashboardBtn.addEventListener('click', () => {
            activateTab('queue');
        });
    }

    function activateTab(tabId) {
        tabs.forEach(t => t.classList.toggle('active-tab', t.dataset.tab === tabId));
        tabContents.forEach(content => content.classList.toggle('hidden', content.id !== tabId));
        if (tabId === 'history') {
            loadHistory();
        }
    }

    // --- Image Viewer ---
    function openImageViewer(src) {
        if (!src || src === 'undefined') {
            console.error("Invalid image source for viewer:", src);
            return;
        }
        viewerImage.src = src;
        imageViewer.classList.remove('hidden');
        imageViewer.classList.add('flex');
    }

    function closeImageViewer() {
        imageViewer.classList.add('hidden');
        imageViewer.classList.remove('flex');
    }

    if (closeImageViewerButton) closeImageViewerButton.addEventListener('click', closeImageViewer);
    if (imageViewer) imageViewer.addEventListener('click', (e) => {
        if (e.target === imageViewer) closeImageViewer();
    });
    window.openImageViewer = openImageViewer;

    // --- Queue Tab: Reddit Posts ---
    async function fetchPosts() {
        if (!getToken()) return;
        if (queueLoader) queueLoader.classList.remove('hidden');
        if (postsContainer) postsContainer.innerHTML = '';
        try {
            const response = await apiFetch(`${API_BASE_URL}/api/posts`);
            if (!response.ok) {
                 const err = await response.json();
                 throw new Error(err.detail || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            renderPosts(data.posts);
        } catch (error) {
            console.error("Failed to fetch posts:", error);
            if (postsContainer) postsContainer.innerHTML = `<p class="text-red-500 col-span-full text-center">Error loading posts: ${error.message}</p>`;
        } finally {
            if (queueLoader) queueLoader.classList.add('hidden');
        }
    }

    function renderPosts(posts) {
        if (!postsContainer) return;
        if (!posts || posts.length === 0) {
            postsContainer.innerHTML = `<p class="text-gray-500 col-span-full text-center">No recent image posts found from Reddit.</p>`;
            return;
        }
        const validPosts = posts.filter(p => p.imageUrl && p.imageUrl.startsWith('http'));
        if (validPosts.length === 0) {
            postsContainer.innerHTML = `<p class="text-gray-500 col-span-full text-center">Found posts, but none had direct image links.</p>`;
            return;
        }
        postsContainer.innerHTML = validPosts.map(post => `
            <div class="card bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transform hover:-translate-y-1 transition-transform duration-300 flex flex-col">
                <div class="relative w-full h-48 cursor-pointer" onclick="window.openImageViewer('${post.imageUrl}')">
                    <img src="${post.thumbnail && post.thumbnail.startsWith('http') ? post.thumbnail : post.imageUrl}" alt="Post thumbnail" class="w-full h-full object-cover">
                </div>
                <div class="p-4 flex flex-col flex-grow">
                    <h3 class="font-bold text-md mb-2 flex-grow" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;" title="${post.title}">${post.title}</h3>
                    <p class="text-gray-600 dark:text-gray-400 text-sm mb-4">/u/${post.author}</p>
                    <button class="analyze-btn mt-auto w-full bg-indigo-600 text-white py-2 rounded-lg hover:bg-indigo-700 transition"
                        data-post-id="${post.id}"
                        data-title="${post.title}"
                        data-description="${post.description || ''}"
                        data-image-url="${post.imageUrl}">
                        Analyze & Edit
                    </button>
                </div>
            </div>
        `).join('');
    }

    if (refreshButton) refreshButton.addEventListener('click', fetchPosts);

    if (postsContainer) {
        postsContainer.addEventListener('click', (e) => {
            const analyzeButton = e.target.closest('.analyze-btn');
            if (analyzeButton) {
                const { postId, title, description, imageUrl } = analyzeButton.dataset;
                handleAnalyzeClick({ button: analyzeButton, postId, title, description, imageUrl });
            }
        });
    }

    async function handleAnalyzeClick({ button, postId, title, description, imageUrl }) {
        button.disabled = true;
        button.innerHTML = `<div class="spinner !h-4 !w-4 !border-2 mx-auto"></div> Analyzing...`;
        try {
            const response = await apiFetch(`${API_BASE_URL}/api/analyze`, {
                method: 'POST',
                body: JSON.stringify({ title, description }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Analysis failed');
            
            const item = { id: postId, title, imageUrl, analysis: data.analysis };
            renderEditor(item);
            activateTab('editor');
        } catch (error) {
            console.error("Analysis request failed:", error);
            alert(`An error occurred during analysis: ${error.message}`);
        } finally {
            button.disabled = false;
            button.innerHTML = 'Analyze & Edit';
        }
    }

    // --- Queue Tab: Image Upload ---
    if (uploadButton && uploadInput) {
        uploadButton.addEventListener('click', () => uploadInput.click());
        uploadInput.addEventListener('change', async (event) => {
            const file = event.target.files[0];
            if (!file) return;

            if (uploadStatus) uploadStatus.textContent = 'Uploading...';
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await apiFetch(`${API_BASE_URL}/api/upload`, { 
                    method: 'POST', 
                    body: formData 
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Upload failed');
                
                if (uploadStatus) uploadStatus.textContent = 'Upload successful! Moving to editor...';
                const item = {
                    id: `upload-${Date.now()}`,
                    title: file.name,
                    imageUrl: data.file_path,
                    analysis: 'Your edit request...'
                };
                renderEditor(item);
                activateTab('editor');
                setTimeout(() => { if (uploadStatus) uploadStatus.textContent = ''; }, 3000);
            } catch (error) {
                console.error('Upload error:', error);
                if (uploadStatus) uploadStatus.textContent = `Error: ${error.message}`;
            }
        });
    }

    // --- Editor View ---
    function renderEditor(item) {
        if (!editorContainer) return;
        editorContainer.innerHTML = `
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-fade-in">
                <div>
                    <h3 class="text-xl font-bold mb-2 truncate" title="${item.title}">${item.title}</h3>
                    <p class="text-gray-400 text-sm mb-4">Original Image</p>
                    <img src="${item.imageUrl}" alt="Original image" class="rounded-lg shadow-lg w-full cursor-pointer" onclick="window.openImageViewer('${item.imageUrl}')">
                </div>
                <div>
                    <h3 class="text-xl font-bold mb-2">Edit Instructions</h3>
                    <p class="text-gray-400 text-sm mb-4">Describe the changes you want to make.</p>
                    <textarea id="edit-prompt" class="w-full h-40 p-3 bg-gray-200 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none text-gray-900 dark:text-gray-100">${item.analysis}</textarea>
                    <button id="generate-edit-btn" data-image-url="${item.imageUrl}" data-id="${item.id}" data-title="${item.title}" class="w-full mt-4 bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 transition text-lg font-semibold">
                        ✨ Generate Image
                    </button>
                    <div id="edit-loader" class="text-center mt-4 hidden">
                        <div class="spinner"></div>
                        <p class="mt-2 text-gray-500">Generating... this can take up to 30 seconds.</p>
                    </div>
                </div>
            </div>
            <div id="edit-result-container" class="mt-8"></div>
        `;
        document.getElementById('generate-edit-btn').addEventListener('click', handleGenerateEdit);
    }
    
    async function handleGenerateEdit(event) {
        const button = event.currentTarget;
        const { imageUrl, id, title } = button.dataset;
        const prompt = document.getElementById('edit-prompt').value;
        const editLoader = document.getElementById('edit-loader');
        const resultContainer = document.getElementById('edit-result-container');

        if (!prompt || prompt.trim() === '' || prompt.trim() === 'Your edit request...') {
            alert("Please enter editing instructions.");
            return;
        }

        button.disabled = true;
        button.innerHTML = `<div class="spinner !h-5 !w-5 !border-2 mx-auto"></div>`;
        if (editLoader) editLoader.classList.remove('hidden');
        if (resultContainer) resultContainer.innerHTML = '';
        
        try {
            const response = await apiFetch(`${API_BASE_URL}/api/edit`, {
                method: 'POST',
                body: JSON.stringify({ imageUrl, prompt }),
            });
            
            const result = await response.json();

            if (result.ok) {
                renderEditResult(imageUrl, result.edited_image_path, id, title, prompt);
                saveToHistory({
                    id: `history-${id}-${Date.now()}`,
                    originalImageUrl: imageUrl,
                    editedImageUrl: result.edited_image_path,
                    postTitle: title,
                    prompt: prompt,
                    timestamp: new Date().toISOString()
                });
            } else {
                throw new Error(result.error || result.detail || 'Failed to generate image.');
            }
        } catch (error) {
            console.error("Edit generation failed:", error);
            if (resultContainer) resultContainer.innerHTML = `<div class="p-4 bg-red-900/50 border border-red-700 rounded-lg text-red-300 text-center"><p class="font-semibold">Generation Failed</p><p class="text-sm">${error.message}</p></div>`;
        } finally {
            button.disabled = false;
            button.innerHTML = '✨ Generate Image';
            if (editLoader) editLoader.classList.add('hidden');
        }
    }

    function renderEditResult(originalUrl, editedPath, id, title, prompt) {
        const resultContainer = document.getElementById('edit-result-container');
        if (!resultContainer) return;
        resultContainer.innerHTML = `
            <div class="card p-6 animate-fade-in">
                <h2 class="text-2xl font-bold mb-4 text-center">Edit Complete!</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h4 class="font-semibold mb-2 text-center">Original</h4>
                        <img src="${originalUrl}" alt="Original" class="rounded-lg shadow-md w-full cursor-pointer" onclick="window.openImageViewer('${originalUrl}')">
                    </div>
                    <div>
                        <h4 class="font-semibold mb-2 text-center">Edited</h4>
                        <img src="${editedPath}" alt="Edited" class="rounded-lg shadow-md w-full cursor-pointer" onclick="window.openImageViewer('${editedPath}')">
                    </div>
                </div>
                <div class="text-center mt-6">
                     <a href="${editedPath}" download="edited-${id}.png" class="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 transition">Download Image</a>
                </div>
            </div>
        `;
    }

    // --- History View ---
    function getHistory() {
        try {
            return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
        } catch (e) {
            console.error("Could not parse history, returning empty array.", e);
            return [];
        }
    }
    
    function saveToHistory(item) {
        try {
            const history = getHistory();
            history.unshift(item); // Add to the beginning
            localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 50))); // Keep max 50 items
        } catch (e) {
            console.error("Could not save to history.", e);
        }
    }

    function loadHistory() {
        const history = getHistory();
        
        if (!historyContainer) return;

        if (history.length === 0) {
            historyContainer.innerHTML = `<div class="text-center py-20 border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg"><p class="text-gray-500">No history yet.</p></div>`;
            if (clearHistoryButton) clearHistoryButton.disabled = true;
            return;
        }

        if (clearHistoryButton) clearHistoryButton.disabled = false;
        historyContainer.innerHTML = history.map(item => `
            <div class="card bg-white dark:bg-gray-800 p-4 rounded-lg shadow-md flex flex-col md:flex-row gap-4 items-center">
                <div class="flex-shrink-0 text-center">
                    <p class="font-semibold text-xs mb-1 text-gray-500 dark:text-gray-400">Original</p>
                    <img src="${item.originalImageUrl}" class="w-24 h-24 object-cover rounded-md cursor-pointer" onclick="window.openImageViewer('${item.originalImageUrl}')">
                </div>
                <div class="flex-shrink-0 text-center">
                    <p class="font-semibold text-xs mb-1 text-gray-500 dark:text-gray-400">Edited</p>
                    <img src="${item.editedImageUrl}" class="w-24 h-24 object-cover rounded-md cursor-pointer" onclick="window.openImageViewer('${item.editedImageUrl}')">
                </div>
                <div class="flex-grow min-w-0">
                    <h4 class="font-bold truncate" title="${item.postTitle}">${item.postTitle}</h4>
                    <p class="text-sm text-gray-500 dark:text-gray-400 italic my-1 truncate" title="${item.prompt}">"${item.prompt}"</p>
                    <p class="text-xs text-gray-400">${new Date(item.timestamp).toLocaleString()}</p>
                </div>
                <div class="flex-shrink-0">
                    <a href="${item.editedImageUrl}" download="history-${item.id}.png" class="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition text-sm">Download</a>
                </div>
            </div>
        `).join('');
    }

    if (clearHistoryButton) {
        clearHistoryButton.addEventListener('click', () => {
            if (confirm('Are you sure you want to clear all edit history?')) {
                localStorage.removeItem(HISTORY_KEY);
                loadHistory();
            }
        });
    }

    // --- Initial Load ---
    checkAuth();
});

