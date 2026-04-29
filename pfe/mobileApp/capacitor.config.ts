import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'io.ionic.starter',
  appName: 'BassarCare', 
  webDir: 'www',
  server: {
    
    url: 'http://192.168.0.155:5000', 
    cleartext: true
  }
};

export default config;