const { contextBridge, ipcRenderer } = require('electron');

// Exposer les APIs sécurisées au renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // Configuration
  getConfig: () => ipcRenderer.invoke('get-config'),
  saveConfig: (config) => ipcRenderer.invoke('save-config', config),
  getAzureConfig: () => ipcRenderer.invoke('get-azure-config'),
  saveAzureConfig: (config) => ipcRenderer.invoke('save-azure-config', config),
  
  // GitHub Token
  saveGitHubToken: (token) => ipcRenderer.invoke('save-github-token', token),
  loadGitHubToken: () => ipcRenderer.invoke('load-github-token'),
  
  // Authentification Microsoft
  microsoftLogin: (authCode) => ipcRenderer.invoke('microsoft-login', authCode),
  refreshMicrosoftToken: () => ipcRenderer.invoke('refresh-microsoft-token'),
  
  // Interface système
  browseJava: () => ipcRenderer.invoke('browse-java'),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  
  // Contrôles de fenêtre
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  maximizeWindow: () => ipcRenderer.invoke('maximize-window'),
  closeWindow: () => ipcRenderer.invoke('close-window'),
  getWindowState: () => ipcRenderer.invoke('get-window-state'),
  
  // Connexion Internet
  isConnectedToInternet: () => ipcRenderer.invoke('is-connected-to-internet'),
  
  // Minecraft
  getMinecraftDirectory: () => ipcRenderer.invoke('get-minecraft-directory'),
  isModpackInstalled: (modpackName) => ipcRenderer.invoke('is-modpack-installed', modpackName),
  
  // Modpacks
  loadModpacks: () => ipcRenderer.invoke('load-modpacks'),
  checkModpackUpdate: (modpack) => ipcRenderer.invoke('check-modpack-update', modpack),
  installModpack: (modpack, progressCallback) => ipcRenderer.invoke('install-modpack', modpack, progressCallback),
  
  // Lancement Minecraft
  launchMinecraft: (modpack, profile, config) => ipcRenderer.invoke('launch-minecraft', modpack, profile, config),
  
  // Statistiques
  loadStats: () => ipcRenderer.invoke('load-stats'),
  updateLaunchStats: () => ipcRenderer.invoke('update-launch-stats'),
  
  // Thèmes et langues
  getAvailableThemes: () => ipcRenderer.invoke('get-available-themes'),
  getAvailableLanguages: () => ipcRenderer.invoke('get-available-languages'),
  loadLanguage: (languageCode) => ipcRenderer.invoke('load-language', languageCode),
  
  // Mises à jour
  checkLauncherUpdate: () => ipcRenderer.invoke('check-launcher-update'),
  
  // Avatars
  getAvatarUrl: (username) => ipcRenderer.invoke('get-avatar-url', username),
  
  // Système de fichiers
  openFolder: (folderPath) => ipcRenderer.invoke('open-folder', folderPath),
  
  // Utilitaires
  isDev: process.argv.includes('--dev')
}); 