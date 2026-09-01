"use client";

import { getContestState } from "../services/contestService";
import { useAsyncData } from "./useAsyncData";

/** Bugünkü yarışma durumu (sözleşme onayı, bugün katıldı mı) - RegisterScreen
 * akışının hangi ekranı göstereceğine karar vermesi için GERÇEK kaynak. */
export function useContestState() {
  return useAsyncData(getContestState, []);
}
