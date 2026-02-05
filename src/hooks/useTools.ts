import { useQuery } from "@tanstack/react-query";
import { fetchTools, fetchToolDetail } from "@/services/api";

export function useTools() {
  return useQuery({
    queryKey: ["tools"],
    queryFn: fetchTools,
  });
}

export function useToolDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["tool", id],
    queryFn: () => fetchToolDetail(id!),
    enabled: !!id,
  });
}
