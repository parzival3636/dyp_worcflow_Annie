import { Capacitor } from '@capacitor/core';
import { StatusBar, Style } from '@capacitor/status-bar';
import { SplashScreen } from '@capacitor/splash-screen';
import { App as CapApp } from '@capacitor/app';

export const isNative = Capacitor.isNativePlatform();
export const platform = Capacitor.getPlatform();

/**
 * Initializes Capacitor plugins when running inside native mobile shell
 */
export async function initCapacitor(navigate) {
  if (!isNative) return;

  try {
    // Hide splash screen smoothly after app is ready
    await SplashScreen.hide({ fadeOutDuration: 300 }).catch(() => {});

    // Set Status Bar
    await StatusBar.setStyle({ style: Style.Dark }).catch(() => {});
    if (platform === 'android') {
      await StatusBar.setBackgroundColor({ color: '#090A0F' }).catch(() => {});
      await StatusBar.setOverlaysWebView({ overlay: false }).catch(() => {});
    }

    // Android hardware back button handler
    CapApp.addListener('backButton', ({ canGoBack }) => {
      const currentPath = window.location.pathname;
      if (currentPath === '/' || currentPath === '/projects' || !canGoBack) {
        CapApp.exitApp();
      } else {
        if (navigate) {
          navigate(-1);
        } else {
          window.history.back();
        }
      }
    });
  } catch (err) {
    console.warn('[Capacitor] Plugin init warning:', err);
  }
}
