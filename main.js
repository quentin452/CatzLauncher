const { app, BrowserWindow, ipcMain, dialog, shell, Menu } = require('electron');
const path = require('path');
const fs = require('fs-extra');
const Store = require('electron-store');
const MinecraftLauncher = require('minecraft-launcher-core');
const fetch = require('node-fetch');
const keytar = require('keytar');

// Configuration du store
const store = new Store({
  name: 'catzlauncher-config',
  defaults: {
    javaPath: '',
    maxMemory: 4,
    jvmArgs: '-XX:+UseConcMarkSweepGC -XX:+CMSIncrementalMode -XX:-UseAdaptiveSizePolicy -Xmn128M',
    theme: 'dark.qss',
    language: 'fr',
    autoCheckUpdates: true,
    autoCheckLauncherUpdates: true,
    githubToken: ''
  }
});

// Configuration Azure
let azureConfig = null;
try {
  azureConfig = require('./azure_config.json');
} catch (error) {
  console.log('Azure config not found, will be created on first run');
}

// Variables globales
let mainWindow;
let launcherAPI;

// Service name pour keytar
const SERVICE_NAME = 'CatzLauncher.GitHubToken';

// Création de la fenêtre principale
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    icon: path.join(__dirname, 'assets/exe/app.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    frame: false,
    titleBarStyle: 'hidden',
    show: false,
    backgroundColor: '#1a1a1a'
  });

  // Charger l'interface
  mainWindow.loadFile(path.join(__dirname, 'renderer/index.html'));

  // Afficher la fenêtre quand elle est prête
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Gestion de la fermeture
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Empêcher la navigation externe
  mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
    event.preventDefault();
    shell.openExternal(navigationUrl);
  });

  // Initialiser l'API Minecraft
  launcherAPI = new MinecraftLauncher();
}

// Gestionnaires IPC pour la communication avec le renderer
ipcMain.handle('get-config', () => {
  return store.store;
});

ipcMain.handle('save-config', (event, config) => {
  store.store = { ...store.store, ...config };
  return true;
});

ipcMain.handle('get-azure-config', () => {
  return azureConfig;
});

ipcMain.handle('save-azure-config', (event, config) => {
  try {
    fs.writeFileSync(path.join(__dirname, 'azure_config.json'), JSON.stringify(config, null, 2));
    azureConfig = config;
    return true;
  } catch (error) {
    console.error('Error saving Azure config:', error);
    return false;
  }
});

ipcMain.handle('save-github-token', async (event, token) => {
  try {
    if (token && token.trim()) {
      await keytar.setPassword(SERVICE_NAME, 'github_token', token);
      return true;
    } else {
      await keytar.deletePassword(SERVICE_NAME, 'github_token');
      return true;
    }
  } catch (error) {
    console.error('Error saving GitHub token:', error);
    return false;
  }
});

ipcMain.handle('load-github-token', async () => {
  try {
    return await keytar.getPassword(SERVICE_NAME, 'github_token');
  } catch (error) {
    console.error('Error loading GitHub token:', error);
    return null;
  }
});

ipcMain.handle('browse-java', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: 'Java Executable', extensions: ['exe'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('open-external', async (event, url) => {
  await shell.openExternal(url);
});

ipcMain.handle('minimize-window', () => {
  mainWindow.minimize();
});

ipcMain.handle('maximize-window', () => {
  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow.maximize();
  }
});

ipcMain.handle('close-window', () => {
  mainWindow.close();
});

ipcMain.handle('get-window-state', () => {
  return {
    isMaximized: mainWindow.isMaximized()
  };
});

// Vérification de la connexion Internet
ipcMain.handle('is-connected-to-internet', async () => {
  try {
    const response = await fetch('https://www.google.com', { 
      method: 'HEAD',
      timeout: 5000 
    });
    return response.ok;
  } catch (error) {
    console.log('Internet connection check failed:', error.message);
    return false;
  }
});

// Obtenir le répertoire Minecraft
ipcMain.handle('get-minecraft-directory', () => {
  return getMinecraftDirectory();
});

// Vérifier si un modpack est installé
ipcMain.handle('is-modpack-installed', async (event, modpackName) => {
  try {
    const minecraftDir = await getMinecraftDirectory();
    const modpackDir = path.join(minecraftDir, 'modpacks', modpackName);
    return await fs.pathExists(modpackDir);
  } catch (error) {
    console.error('Error checking modpack installation:', error);
    return false;
  }
});

// Installer un modpack
ipcMain.handle('install-modpack', async (event, modpack, progressCallback) => {
  try {
    // Simulation d'installation pour l'instant
    console.log('Installing modpack:', modpack.name);
    
    // Simuler la progression
    for (let i = 0; i <= 100; i += 10) {
      if (progressCallback) {
        progressCallback(i);
      }
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    
    return { success: true };
  } catch (error) {
    console.error('Error installing modpack:', error);
    return { success: false, error: error.message };
  }
});

// Lancer Minecraft
ipcMain.handle('launch-minecraft', async (event, modpack, profile, config) => {
  try {
    console.log('Launching Minecraft for modpack:', modpack.name);
    console.log('Profile:', profile);
    console.log('Config:', config);
    
    // Simulation de lancement pour l'instant
    return { success: true };
  } catch (error) {
    console.error('Error launching Minecraft:', error);
    return { success: false, error: error.message };
  }
});

// Mettre à jour les statistiques de lancement
ipcMain.handle('update-launch-stats', async () => {
  try {
    const statsPath = path.join(__dirname, 'user_stats.json');
    let stats = {};
    
    if (await fs.pathExists(statsPath)) {
      stats = await fs.readJson(statsPath);
    }
    
    stats.launch_count = (stats.launch_count || 0) + 1;
    stats.last_activity = new Date().toISOString();
    
    await fs.writeJson(statsPath, stats, { spaces: 2 });
    return true;
  } catch (error) {
    console.error('Error updating launch stats:', error);
    return false;
  }
});

// Charger les statistiques
ipcMain.handle('load-stats', async () => {
  try {
    const statsPath = path.join(__dirname, 'user_stats.json');
    
    if (await fs.pathExists(statsPath)) {
      return await fs.readJson(statsPath);
    } else {
      return {
        last_activity: null,
        playtime: 0,
        launch_count: 0,
        login_count: 0
      };
    }
  } catch (error) {
    console.error('Error loading stats:', error);
    return {
      last_activity: null,
      playtime: 0,
      launch_count: 0,
      login_count: 0
    };
  }
});

// Charger les modpacks
ipcMain.handle('load-modpacks', async () => {
  try {
    const modpacksPath = path.join(__dirname, 'modpacks.json');
    
    if (await fs.pathExists(modpacksPath)) {
      return await fs.readJson(modpacksPath);
    } else {
      // Retourner des modpacks de test par défaut
      return [
        {
          name: "Test Modpack 1",
          version: "1.19.2",
          forge_version: "43.2.0",
          java_version: "17",
          estimated_mb: 500,
          url: "https://example.com/modpack1.zip",
          last_modified: "2024-01-01"
        },
        {
          name: "Test Modpack 2",
          version: "1.18.2",
          forge_version: "40.2.0",
          java_version: "17",
          estimated_mb: 300,
          url: "https://example.com/modpack2.zip",
          last_modified: "2024-01-02"
        }
      ];
    }
  } catch (error) {
    console.error('Error loading modpacks:', error);
    return [];
  }
});

// Charger les traductions
ipcMain.handle('load-language', async (event, languageCode) => {
  try {
    const langPath = path.join(__dirname, 'assets', 'languages', `${languageCode}.json`);
    
    if (await fs.pathExists(langPath)) {
      return await fs.readJson(langPath);
    } else {
      // Fallback vers français
      const fallbackPath = path.join(__dirname, 'assets', 'languages', 'fr.json');
      if (await fs.pathExists(fallbackPath)) {
        return await fs.readJson(fallbackPath);
      } else {
        return {};
      }
    }
  } catch (error) {
    console.error('Error loading language:', error);
    return {};
  }
});

// Obtenir les thèmes disponibles
ipcMain.handle('get-available-themes', async () => {
  try {
    const stylesPath = path.join(__dirname, 'assets', 'styles');
    const files = await fs.readdir(stylesPath);
    return files.filter(file => file.endsWith('.qss'));
  } catch (error) {
    console.error('Error getting available themes:', error);
    return ['dark.qss', 'light.qss'];
  }
});

// Obtenir les langues disponibles
ipcMain.handle('get-available-languages', async () => {
  try {
    const languagesPath = path.join(__dirname, 'assets', 'languages');
    const files = await fs.readdir(languagesPath);
    return files.filter(file => file.endsWith('.json')).map(file => file.replace('.json', ''));
  } catch (error) {
    console.error('Error getting available languages:', error);
    return ['fr', 'en'];
  }
});

// Vérifier les mises à jour du launcher
ipcMain.handle('check-launcher-update', async () => {
  try {
    const currentVersion = getLocalLauncherVersion();
    const repoUrl = 'https://api.github.com/repos/quentin452/CatzLauncher/contents/version.txt';
    
    const response = await fetch(repoUrl);
    const data = await response.json();
    
    if (data.tag_name && data.tag_name !== currentVersion) {
      return {
        hasUpdate: true,
        currentVersion: currentVersion,
        newVersion: data.tag_name,
        downloadUrl: data.html_url
      };
    } else {
      return { hasUpdate: false };
    }
  } catch (error) {
    console.error('Error checking launcher update:', error);
    return { hasUpdate: false };
  }
});

// Obtenir l'URL de l'avatar Minecraft
ipcMain.handle('get-avatar-url', (event, username) => {
  return `https://minotar.net/armor/body/${username}/120`;
});

// Ouvrir un dossier
ipcMain.handle('open-folder', async (event, folderPath) => {
  try {
    const { shell } = require('electron');
    await shell.openPath(folderPath);
    return true;
  } catch (error) {
    console.error('Error opening folder:', error);
    return false;
  }
});

// Gestionnaires pour les authentifications Microsoft
ipcMain.handle('microsoft-login', async (event, authCode) => {
  try {
    if (!azureConfig || !azureConfig.client_id) {
      throw new Error('Azure Client ID not configured');
    }

    // Étape 1: Échanger le code contre un token Microsoft
    const msTokenData = await exchangeCodeForToken(authCode, azureConfig.client_id);
    
    // Étape 2: Authentifier avec Xbox Live
    const xblData = await authenticateWithXbox(msTokenData.access_token);
    
    // Étape 3: Authentifier avec XSTS
    const xstsData = await authenticateWithXsts(xblData.Token);
    
    // Étape 4: Login avec Minecraft
    const mcData = await loginWithMinecraft(xblData.DisplayClaims.xui[0].uhs, xstsData.Token);
    
    // Étape 5: Récupérer le profil Minecraft
    const profile = await getMinecraftProfile(mcData.access_token);
    
    // Sauvegarder le refresh token si disponible
    if (msTokenData.refresh_token) {
      store.set('refresh_token', msTokenData.refresh_token);
    }
    
    return {
      profile: profile,
      access_token: mcData.access_token,
      refresh_token: msTokenData.refresh_token
    };
    
  } catch (error) {
    console.error('Microsoft login error:', error);
    throw error;
  }
});

ipcMain.handle('refresh-microsoft-token', async (event) => {
  try {
    const refreshToken = store.get('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    if (!azureConfig || !azureConfig.client_id) {
      throw new Error('Azure Client ID not configured');
    }

    // Rafraîchir le token Microsoft
    const msTokenData = await refreshMsToken(refreshToken, azureConfig.client_id);
    
    // Réauthentifier avec Xbox Live
    const xblData = await authenticateWithXbox(msTokenData.access_token);
    
    // Réauthentifier avec XSTS
    const xstsData = await authenticateWithXsts(xblData.Token);
    
    // Relogin avec Minecraft
    const mcData = await loginWithMinecraft(xblData.DisplayClaims.xui[0].uhs, xstsData.Token);
    
    // Récupérer le profil Minecraft
    const profile = await getMinecraftProfile(mcData.access_token);
    
    // Sauvegarder le nouveau refresh token
    if (msTokenData.refresh_token) {
      store.set('refresh_token', msTokenData.refresh_token);
    }
    
    return {
      profile: profile,
      access_token: mcData.access_token,
      refresh_token: msTokenData.refresh_token
    };
    
  } catch (error) {
    console.error('Token refresh error:', error);
    throw error;
  }
});

// Gestionnaires pour les modpacks
ipcMain.handle('check-modpack-update', async (event, modpack) => {
  try {
    const token = await keytar.getPassword(SERVICE_NAME, 'github_token');
    const headers = { 'User-Agent': 'CatzLauncher' };
    if (token) {
      headers['Authorization'] = `token ${token}`;
    }

    // Extraire les informations du repo depuis l'URL
    const urlParts = modpack.url.split('/');
    const owner = urlParts[3];
    const repo = urlParts[4];
    const branch = urlParts[7].replace('.zip', '');

    const apiUrl = `https://api.github.com/repos/${owner}/${repo}/commits/${branch}`;
    const response = await fetch(apiUrl, { headers });
    
    if (!response.ok) {
      throw new Error(`GitHub API error: ${response.status}`);
    }

    const commitData = await response.json();
    const lastCommit = commitData.sha;
    const lastModified = commitData.commit.author.date;
    
    return {
      hasUpdate: lastCommit !== modpack.last_commit,
      newCommit: lastCommit,
      newModified: lastModified,
      modpack: modpack
    };
  } catch (error) {
    console.error('Error checking modpack update:', error);
    throw error;
  }
});

// Fonctions d'authentification Microsoft
async function exchangeCodeForToken(authCode, clientId) {
  const data = {
    client_id: clientId,
    code: authCode,
    grant_type: 'authorization_code',
    redirect_uri: 'https://login.live.com/oauth20_desktop.srf'
  };

  const response = await fetch('https://login.live.com/oauth20_token.srf', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: new URLSearchParams(data)
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to exchange code for token: ${response.status} ${errorText}`);
  }

  return await response.json();
}

async function refreshMsToken(refreshToken, clientId) {
  const data = {
    client_id: clientId,
    refresh_token: refreshToken,
    grant_type: 'refresh_token'
  };

  const response = await fetch('https://login.live.com/oauth20_token.srf', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: new URLSearchParams(data)
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to refresh token: ${response.status} ${errorText}`);
  }

  return await response.json();
}

async function authenticateWithXbox(accessToken) {
  const data = {
    Properties: {
      AuthMethod: 'RPS',
      SiteName: 'user.auth.xboxlive.com',
      RpsTicket: `d=${accessToken}`
    },
    RelyingParty: 'http://auth.xboxlive.com',
    TokenType: 'JWT'
  };

  const response = await fetch('https://user.auth.xboxlive.com/user/authenticate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Xbox Live authentication failed: ${response.status} ${errorText}`);
  }

  return await response.json();
}

async function authenticateWithXsts(xblToken) {
  const data = {
    Properties: {
      SandboxId: 'RETAIL',
      UserTokens: [xblToken]
    },
    RelyingParty: 'rp://api.minecraftservices.com/',
    TokenType: 'JWT'
  };

  const response = await fetch('https://xsts.auth.xboxlive.com/xsts/authorize', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`XSTS authentication failed: ${response.status} ${errorText}`);
  }

  return await response.json();
}

async function loginWithMinecraft(userHash, xstsToken) {
  const data = {
    identityToken: `XBL3.0 x=${userHash};${xstsToken}`
  };

  const response = await fetch('https://api.minecraftservices.com/authentication/login_with_xbox', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Minecraft login failed: ${response.status} ${errorText}`);
  }

  return await response.json();
}

async function getMinecraftProfile(minecraftToken) {
  const response = await fetch('https://api.minecraftservices.com/minecraft/profile', {
    headers: {
      'Authorization': `Bearer ${minecraftToken}`
    }
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to get Minecraft profile: ${response.status} ${errorText}`);
  }

  return await response.json();
}

// Gestionnaires pour les mises à jour du launcher
function getLocalLauncherVersion() {
  try {
    const versionPath = path.join(__dirname, 'version.txt');
    if (fs.existsSync(versionPath)) {
      return fs.readFileSync(versionPath, 'utf8').trim();
    }
    return 'inconnue';
  } catch (e) {
    return 'inconnue';
  }
}

// Fonction helper pour obtenir le répertoire Minecraft
function getMinecraftDirectory() {
  const os = require('os');
  const platform = process.platform;
  
  if (platform === 'win32') {
    return path.join(os.homedir(), 'AppData', 'Roaming', '.minecraft');
  } else if (platform === 'darwin') {
    return path.join(os.homedir(), 'Library', 'Application Support', 'minecraft');
  } else {
    return path.join(os.homedir(), '.minecraft');
  }
}

// Initialisation de l'application
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