import { create } from "zustand";
import { getMeApi, loginApi, logoutApi, type UserProfile } from "../api/auth";
import { ApiError } from "../api/client";

interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authInitialized: boolean;
  error: string | null;

  checkAuth: () => Promise<void>;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<UserProfile>;
  logout: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  authInitialized: false,
  error: null,

  clearError: () => set({ error: null }),

  checkAuth: async () => {
    set({ isLoading: true });
    try {
      const user = await getMeApi();
      set({
        user,
        isAuthenticated: true,
        isLoading: false,
        authInitialized: true,
        error: null,
      });
    } catch {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        authInitialized: true,
      });
    }
  },

  login: async (email, password, rememberMe = false) => {
    set({ isLoading: true, error: null });
    try {
      const response = await loginApi({ email, password, remember_me: rememberMe });
      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        authInitialized: true,
        error: null,
      });
      return response.user;
    } catch (err) {
      let message = "Unable to connect to NetraKon AI. Please try again.";
      if (err instanceof ApiError) {
        message = err.message;
      }
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: message,
      });
      throw new Error(message);
    }
  },

  logout: async () => {
    set({ isLoading: true });
    try {
      await logoutApi();
    } catch {
      // Ignore logout API failures
    } finally {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        authInitialized: true,
        error: null,
      });
    }
  },
}));
