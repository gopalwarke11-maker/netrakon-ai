import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  getAlertWebSocketUrl,
  intrusionEventToAlert,
  parseBehaviorEvent,
  parseIntrusionEvent,
} from "../api/alertWebSocket";
import { useAlertStore } from "../state/alertStore";
import type { ApiAlert } from "../types/api";

export function useAlertWebSocket() {
  const queryClient = useQueryClient();
  const setConnectionStatus = useAlertStore(
    (state) => state.setConnectionStatus,
  );

  useEffect(() => {
    let socket: WebSocket | undefined;
    let retryTimer: number | undefined;
    let stopped = false;
    let attempts = 0;
    const connect = () => {
      if (
        stopped ||
        socket?.readyState === WebSocket.OPEN ||
        socket?.readyState === WebSocket.CONNECTING
      )
        return;
      setConnectionStatus("CONNECTING");
      socket = new WebSocket(getAlertWebSocketUrl());
      socket.onopen = () => {
        attempts = 0;
        setConnectionStatus("CONNECTED");
      };
      socket.onmessage = (message) => {
        try {
          const value = JSON.parse(message.data) as unknown;
          const behaviorEvent = parseBehaviorEvent(value);
          if (behaviorEvent) {
            void queryClient.invalidateQueries({
              queryKey: ["behaviors", behaviorEvent.camera_id],
            });
            return;
          }
          const event = parseIntrusionEvent(value);
          if (event) {
            queryClient.setQueryData<ApiAlert[]>(["alerts"], (current = []) =>
              current.some((alert) => alert.id === event.alert_id)
                ? current
                : [intrusionEventToAlert(event), ...current],
            );
          }
        } catch {
          /* Ignore malformed messages from the stream. */
        }
      };
      socket.onclose = () => {
        setConnectionStatus("DISCONNECTED");
        if (!stopped) {
          const delay = Math.min(1000 * 2 ** attempts++, 10000);
          retryTimer = window.setTimeout(connect, delay);
        }
      };
      socket.onerror = () => socket?.close();
    };
    connect();
    return () => {
      stopped = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      socket?.close();
    };
  }, [queryClient, setConnectionStatus]);
}
