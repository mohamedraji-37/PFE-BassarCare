import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'io.ionic.starter',
  appName: 'BassarCare', 
  webDir: 'www',
  server: {
    
    url: 'http://10.115.91.233:5000', 
    cleartext: true
  }
};

export default config;