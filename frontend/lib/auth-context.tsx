"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  clearToken,
  getMe,
  getToken,
  login as apiLogin,
  logout as apiLogout,
  setToken,
  type UserOut,
} from "./api";

interface AuthContextValue {
  user: UserOut | undefined;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage is unavailable during SSR; deferring to an effect avoids a hydration mismatch.
    setHasToken(!!getToken());
    setReady(true);
  }, []);

  const { data: user, isLoading: isUserLoading } = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    enabled: ready && hasToken,
    retry: false,
  });

  const loginMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => apiLogin(email, password),
    onSuccess: (data) => {
      setToken(data.access_token);
      setHasToken(true);
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });

  function logoutUser() {
    apiLogout().catch(() => {});
    clearToken();
    setHasToken(false);
    queryClient.removeQueries({ queryKey: ["me"] });
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: hasToken && !!user,
        isLoading: !ready || (hasToken && isUserLoading),
        login: async (email, password) => {
          await loginMutation.mutateAsync({ email, password });
        },
        logout: logoutUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
