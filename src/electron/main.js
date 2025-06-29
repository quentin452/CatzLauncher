const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron');
const path = require('path');
const axios = require('axios');
const fs = require('fs');
const os = require('os');

console.log('Démarrage de CatzLauncher Electron...');
console.log('Chemin de l\'application:', app.getAppPath());
console.log('Chemin du fichier principal:', __filename);

// Configuration Azure - basée sur le code Python
const AZURE_CONFIG_PATH = path.join(app.getAppPath(), 'azure_config.json');
const REFRESH_TOKEN_PATH = path.join(os.homedir(), '.catzlauncher_refresh_token.json');

// Client ID par défaut (celui de Minecraft)
const DEFAULT_CLIENT_ID = '00000000402b5328';

// Fonction pour charger la configuration Azure
function loadAzureConfig() {
    try {
        if (fs.existsSync(AZURE_CONFIG_PATH)) {
            const config = JSON.parse(fs.readFileSync(AZURE_CONFIG_PATH, 'utf-8'));
            const clientId = config.client_id;
            
            if (clientId && clientId !== 'VOTRE_CLIENT_ID_AZURE_ICI') {
                return clientId;
            }
        }
    } catch (error) {
        console.error('Erreur lors du chargement de la configuration Azure:', error);
    }
    
    // Créer le fichier de configuration par défaut s'il n'existe pas
    if (!fs.existsSync(AZURE_CONFIG_PATH)) {
        const defaultConfig = {
            "//": "Veuillez remplacer la valeur ci-dessous par votre 'ID d'application (client)' depuis le portail Azure.",
            "client_id": "VOTRE_CLIENT_ID_AZURE_ICI"
        };
        try {
            fs.writeFileSync(AZURE_CONFIG_PATH, JSON.stringify(defaultConfig, null, 4), 'utf-8');
            console.log('Fichier de configuration Azure créé:', AZURE_CONFIG_PATH);
        } catch (error) {
            console.error('Erreur lors de la création du fichier de configuration Azure:', error);
        }
    }
    
    return DEFAULT_CLIENT_ID;
}

// Obtenir le Client ID
const MICROSOFT_CLIENT_ID = loadAzureConfig();
const MICROSOFT_REDIRECT_URI = 'https://login.live.com/oauth20_desktop.srf';

function createWindow() {
  console.log('Création de la fenêtre principale...');
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    icon: path.join(__dirname, '../../assets/icons/app.ico'),
    titleBarStyle: 'hidden',
    frame: false
  });

  const htmlPath = path.join(__dirname, '../main/index.html');
  console.log('Chargement du fichier HTML:', htmlPath);
  console.log('Le fichier existe:', fs.existsSync(htmlPath));
  
  win.loadFile(htmlPath);

  // Ouvrir les outils de développement en mode développement
  if (process.argv.includes('--dev')) {
    win.webContents.openDevTools();
  }

  // Gestion des événements IPC pour les contrôles de fenêtre
  ipcMain.on('window-minimize', () => {
    win.minimize();
  });
  ipcMain.on('window-maximize', () => {
    if (win.isMaximized()) {
      win.unmaximize();
    } else {
      win.maximize();
    }
  });
  ipcMain.on('window-close', () => {
    win.close();
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Fonction pour sauvegarder le refresh_token
function saveRefreshToken(token) {
  try {
    fs.writeFileSync(REFRESH_TOKEN_PATH, JSON.stringify({ refresh_token: token }), 'utf-8');
  } catch (e) {
    console.error('Erreur lors de la sauvegarde du refresh_token:', e);
  }
}

// Fonction pour charger le refresh_token
function loadRefreshToken() {
  try {
    if (fs.existsSync(REFRESH_TOKEN_PATH)) {
      const data = fs.readFileSync(REFRESH_TOKEN_PATH, 'utf-8');
      return JSON.parse(data).refresh_token;
    }
  } catch (e) {
    console.error('Erreur lors du chargement du refresh_token:', e);
  }
  return null;
}

// Fonction pour rafraîchir le token Microsoft (améliorée basée sur le code Python)
async function refreshMicrosoftToken(refresh_token) {
  try {
    console.log('🔄 Actualisation du token...');
    const tokenResponse = await axios.post('https://login.live.com/oauth20_token.srf',
      new URLSearchParams({
        client_id: MICROSOFT_CLIENT_ID,
        refresh_token: refresh_token,
        grant_type: 'refresh_token',
        redirect_uri: MICROSOFT_REDIRECT_URI
      }).toString(),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        timeout: 10000
      }
    );
    return tokenResponse.data;
  } catch (e) {
    console.error('Erreur lors du refresh Microsoft token:', e.response?.data || e.message);
    return null;
  }
}

// Fonction pour échanger le code contre un token (améliorée)
async function exchangeCodeForToken(code) {
  try {
    console.log('🔐 Échange du code...');
    
    const tokenResponse = await axios.post('https://login.live.com/oauth20_token.srf', 
      new URLSearchParams({
        client_id: MICROSOFT_CLIENT_ID,
        code: code,
        grant_type: 'authorization_code',
        redirect_uri: MICROSOFT_REDIRECT_URI
      }).toString(),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        timeout: 10000
      }
    );

    const accessToken = tokenResponse.data.access_token;
    const refreshToken = tokenResponse.data.refresh_token;
    if (refreshToken) saveRefreshToken(refreshToken);
    console.log('Token Microsoft obtenu');

    return await authenticateWithMinecraft(accessToken);

  } catch (error) {
    console.error('Erreur lors de l\'échange du code:', error.response?.data || error.message);
    throw new Error(`Erreur d'authentification: ${error.response?.data?.error_description || error.message}`);
  }
}

// Fonction d'authentification avec Minecraft (basée sur le code Python)
async function authenticateWithMinecraft(msAccessToken) {
  try {
    console.log('🎮 Authentification Xbox...');
    const xblResponse = await axios.post('https://user.auth.xboxlive.com/user/authenticate', {
      Properties: {
        AuthMethod: 'RPS',
        SiteName: 'user.auth.xboxlive.com',
        RpsTicket: `d=${msAccessToken}`
      },
      RelyingParty: 'http://auth.xboxlive.com',
      TokenType: 'JWT'
    }, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      timeout: 10000
    });

    const xblToken = xblResponse.data.Token;
    console.log('Token Xbox Live obtenu');

    console.log('🔒 Authentification XSTS...');
    const xstsResponse = await axios.post('https://xsts.auth.xboxlive.com/xsts/authorize', {
      Properties: {
        SandboxId: 'RETAIL',
        UserTokens: [xblToken]
      },
      RelyingParty: 'rp://api.minecraftservices.com/',
      TokenType: 'JWT'
    }, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      timeout: 10000
    });

    const xstsToken = xstsResponse.data.Token;
    const userHash = xstsResponse.data.DisplayClaims.xui[0].uhs;
    console.log('Token XSTS obtenu');

    console.log('⚡ Authentification Minecraft...');
    const mcResponse = await axios.post('https://api.minecraftservices.com/authentication/login_with_xbox', {
      identityToken: `XBL3.0 x=${userHash};${xstsToken}`
    }, {
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 10000
    });

    const mcAccessToken = mcResponse.data.access_token;
    console.log('Token Minecraft obtenu');

    console.log('👤 Récupération du profil...');
    const profileResponse = await axios.get('https://api.minecraftservices.com/minecraft/profile', {
      headers: {
        'Authorization': `Bearer ${mcAccessToken}`
      },
      timeout: 10000
    });

    const profile = profileResponse.data;
    console.log('Profil Minecraft récupéré:', profile.name);

    return {
      name: profile.name,
      email: profile.name + '@minecraft.com',
      avatar: `https://minotar.net/armor/body/${profile.name}/120`,
      gamertag: profile.name,
      uuid: profile.id,
      access_token: mcAccessToken
    };

  } catch (error) {
    console.error('Erreur lors de l\'authentification Minecraft:', error.response?.data || error.message);
    throw new Error(`Erreur d'authentification Minecraft: ${error.response?.data?.error_description || error.message}`);
  }
}

// Handler principal amélioré
ipcMain.handle('microsoft-login', async (event) => {
  try {
    // Vérifier si le Client ID est configuré
    if (MICROSOFT_CLIENT_ID === 'VOTRE_CLIENT_ID_AZURE_ICI') {
      throw new Error('Client ID Azure non configuré. Veuillez configurer votre Client ID dans azure_config.json');
    }

    // 1. Tenter la reconnexion automatique
    const savedRefreshToken = loadRefreshToken();
    if (savedRefreshToken) {
      console.log('Tentative de reconnexion automatique...');
      const tokenData = await refreshMicrosoftToken(savedRefreshToken);
      if (tokenData && tokenData.access_token && tokenData.refresh_token) {
        saveRefreshToken(tokenData.refresh_token);
        try {
          const profile = await authenticateWithMinecraft(tokenData.access_token);
          console.log('Reconnexion automatique réussie:', profile.name);
          return profile;
        } catch (e) {
          console.error('Erreur lors de la reconnexion automatique Minecraft:', e);
          // Suppression du refresh_token si erreur
          try { fs.unlinkSync(REFRESH_TOKEN_PATH); } catch {}
          // On continue avec le flux normal
        }
      } else {
        // Token invalide, suppression
        try { fs.unlinkSync(REFRESH_TOKEN_PATH); } catch {}
      }
    }

    // 2. Flux normal (fenêtre d'auth Microsoft)
    return new Promise((resolve, reject) => {
      let win = BrowserWindow.getFocusedWindow();
      if (!win) {
        const allWins = BrowserWindow.getAllWindows();
        if (allWins.length > 0) win = allWins[0];
      }
      
      const MICROSOFT_AUTH_URL = `https://login.live.com/oauth20_authorize.srf?client_id=${MICROSOFT_CLIENT_ID}&response_type=code&redirect_uri=${encodeURIComponent(MICROSOFT_REDIRECT_URI)}&scope=XboxLive.signin%20offline_access%20openid%20profile%20email`;
      
      console.log('Création de la fenêtre d\'auth Microsoft, parent:', !!win);
      const authWin = new BrowserWindow({
        width: 500,
        height: 700,
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true
        },
        parent: win,
        modal: true,
        show: true
      });

      function handleUrl(url) {
        const codeMatch = url.match(/[\?&]code=([^&]+)/);
        if (codeMatch) {
          const code = codeMatch[1];
          authWin.close();
          exchangeCodeForToken(code).then(profile => {
            resolve(profile);
          }).catch(error => {
            reject(error);
          });
        }
      }

      authWin.webContents.on('will-redirect', (event, url) => handleUrl(url));
      authWin.webContents.on('will-navigate', (event, url) => handleUrl(url));
      authWin.on('closed', () => reject(new Error('Authentification annulée')));
      authWin.loadURL(MICROSOFT_AUTH_URL);
    });

  } catch (error) {
    console.error('Erreur lors de l\'authentification Microsoft:', error);
    throw error;
  }
});

// Gestionnaire pour le code d'authentification manuel
ipcMain.on('microsoft-login-code', async (event, url) => {
  try {
    const codeMatch = url.match(/[\?&]code=([^&]+)/);
    if (codeMatch) {
      const code = codeMatch[1];
      const profile = await exchangeCodeForToken(code);
      event.sender.send('microsoft-login-result', profile);
    } else {
      event.sender.send('microsoft-login-result', null);
    }
  } catch (error) {
    console.error('Erreur lors du traitement du code manuel:', error);
    event.sender.send('microsoft-login-result', null);
  }
});

// Gestionnaire pour ouvrir les URLs externes
ipcMain.on('open-external-url', (event, url) => {
  shell.openExternal(url);
});

// Nouveau gestionnaire pour vérifier la configuration Azure
ipcMain.handle('check-azure-config', () => {
  const clientId = loadAzureConfig();
  return {
    configured: clientId !== 'VOTRE_CLIENT_ID_AZURE_ICI',
    clientId: clientId,
    configPath: AZURE_CONFIG_PATH
  };
}); 