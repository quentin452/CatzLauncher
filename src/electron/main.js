const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron');
const path = require('path');
const axios = require('axios');
const fs = require('fs');
const os = require('os');

console.log('Démarrage de CatzLauncher Electron...');
console.log('Chemin de l\'application:', app.getAppPath());
console.log('Chemin du fichier principal:', __filename);

const MICROSOFT_CLIENT_ID = '00000000402b5328'; // Client ID public de démonstration Minecraft
const MICROSOFT_REDIRECT_URI = 'https://login.live.com/oauth20_desktop.srf';
const MICROSOFT_AUTH_URL = `https://login.live.com/oauth20_authorize.srf?client_id=${MICROSOFT_CLIENT_ID}&response_type=code&redirect_uri=${encodeURIComponent(MICROSOFT_REDIRECT_URI)}&scope=XboxLive.signin%20offline_access%20openid%20profile%20email`;
const REFRESH_TOKEN_PATH = path.join(os.homedir(), '.catzlauncher_refresh_token.json');

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

// Fonction pour rafraîchir le token Microsoft
async function refreshMicrosoftToken(refresh_token) {
  try {
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
        }
      }
    );
    return tokenResponse.data;
  } catch (e) {
    console.error('Erreur lors du refresh Microsoft token:', e);
    return null;
  }
}

// Handler principal
ipcMain.handle('microsoft-login', async (event) => {
  // 1. Tenter la reconnexion automatique
  const savedRefreshToken = loadRefreshToken();
  if (savedRefreshToken) {
    const tokenData = await refreshMicrosoftToken(savedRefreshToken);
    if (tokenData && tokenData.access_token && tokenData.refresh_token) {
      saveRefreshToken(tokenData.refresh_token);
      try {
        // Étape 2: Authentification Xbox Live
        const xblResponse = await axios.post('https://user.auth.xboxlive.com/user/authenticate', {
          Properties: {
            AuthMethod: 'RPS',
            SiteName: 'user.auth.xboxlive.com',
            RpsTicket: `d=${tokenData.access_token}`
          },
          RelyingParty: 'http://auth.xboxlive.com',
          TokenType: 'JWT'
        }, {
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });
        const xblToken = xblResponse.data.Token;
        // Étape 3: Authentification XSTS
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
          }
        });
        const xstsToken = xstsResponse.data.Token;
        const userHash = xstsResponse.data.DisplayClaims.xui[0].uhs;
        // Étape 4: Authentification Minecraft
        const mcResponse = await axios.post('https://api.minecraftservices.com/authentication/login_with_xbox', {
          identityToken: `XBL3.0 x=${userHash};${xstsToken}`
        }, {
          headers: {
            'Content-Type': 'application/json'
          }
        });
        const mcAccessToken = mcResponse.data.access_token;
        // Étape 5: Récupérer le profil Minecraft
        const profileResponse = await axios.get('https://api.minecraftservices.com/minecraft/profile', {
          headers: {
            'Authorization': `Bearer ${mcAccessToken}`
          }
        });
        const profile = profileResponse.data;
        return {
          name: profile.name,
          email: profile.name + '@minecraft.com',
          avatar: `https://crafatar.com/avatars/${profile.id}?overlay=true`,
          gamertag: profile.name,
          uuid: profile.id,
          access_token: mcAccessToken
        };
      } catch (e) {
        console.error('Erreur lors de la reconnexion automatique Minecraft:', e);
        // Suppression du refresh_token si erreur
        try { fs.unlinkSync(REFRESH_TOKEN_PATH); } catch {}
        // Notification utilisateur
        const win = BrowserWindow.getFocusedWindow();
        if (win) {
          dialog.showMessageBox(win, {
            type: 'warning',
            title: 'Reconnexion automatique échouée',
            message: 'Votre session a expiré ou est invalide. Veuillez vous reconnecter.'
          });
        }
        // On continue avec le flux normal
      }
    } else {
      // Token invalide, suppression et notification
      try { fs.unlinkSync(REFRESH_TOKEN_PATH); } catch {}
      const win = BrowserWindow.getFocusedWindow();
      if (win) {
        dialog.showMessageBox(win, {
          type: 'warning',
          title: 'Reconnexion automatique échouée',
          message: 'Votre session a expiré ou est invalide. Veuillez vous reconnecter.'
        });
      }
    }
  }

  // 2. Sinon, flux normal (fenêtre d'auth Microsoft)
  return new Promise((resolve) => {
    let win = BrowserWindow.getFocusedWindow();
    if (!win) {
      const allWins = BrowserWindow.getAllWindows();
      if (allWins.length > 0) win = allWins[0];
    }
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
        });
      }
    }

    authWin.webContents.on('will-redirect', (event, url) => handleUrl(url));
    authWin.webContents.on('will-navigate', (event, url) => handleUrl(url));
    authWin.on('closed', () => resolve(null));
    authWin.loadURL(MICROSOFT_AUTH_URL);
  });
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

async function exchangeCodeForToken(code) {
  try {
    console.log('Code d\'autorisation reçu:', code);
    
    // Étape 1: Échanger le code contre un token Microsoft
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
        }
      }
    );

    const accessToken = tokenResponse.data.access_token;
    const refreshToken = tokenResponse.data.refresh_token;
    if (refreshToken) saveRefreshToken(refreshToken);
    console.log('Token Microsoft obtenu');

    // Étape 2: Authentification Xbox Live
    const xblResponse = await axios.post('https://user.auth.xboxlive.com/user/authenticate', {
      Properties: {
        AuthMethod: 'RPS',
        SiteName: 'user.auth.xboxlive.com',
        RpsTicket: `d=${accessToken}`
      },
      RelyingParty: 'http://auth.xboxlive.com',
      TokenType: 'JWT'
    }, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });

    const xblToken = xblResponse.data.Token;
    console.log('Token Xbox Live obtenu');

    // Étape 3: Authentification XSTS
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
      }
    });

    const xstsToken = xstsResponse.data.Token;
    const userHash = xstsResponse.data.DisplayClaims.xui[0].uhs;
    console.log('Token XSTS obtenu');

    // Étape 4: Authentification Minecraft
    const mcResponse = await axios.post('https://api.minecraftservices.com/authentication/login_with_xbox', {
      identityToken: `XBL3.0 x=${userHash};${xstsToken}`
    }, {
      headers: {
        'Content-Type': 'application/json'
      }
    });

    const mcAccessToken = mcResponse.data.access_token;
    console.log('Token Minecraft obtenu');

    // Étape 5: Récupérer le profil Minecraft
    const profileResponse = await axios.get('https://api.minecraftservices.com/minecraft/profile', {
      headers: {
        'Authorization': `Bearer ${mcAccessToken}`
      }
    });

    const profile = profileResponse.data;
    console.log('Profil Minecraft récupéré:', profile.name);

    return {
      name: profile.name,
      email: profile.name + '@minecraft.com',
      avatar: `https://crafatar.com/avatars/${profile.id}?overlay=true`,
      gamertag: profile.name,
      uuid: profile.id,
      access_token: mcAccessToken
    };

  } catch (error) {
    console.error('Erreur lors de l\'authentification Microsoft:', error);
    
    // En cas d'erreur, retourner un utilisateur de démonstration
    return {
      name: 'Utilisateur Connecté',
      email: 'demo@example.com',
      avatar: '../assets/textures/default-avatar.png',
      gamertag: 'Joueur'
    };
  }
} 