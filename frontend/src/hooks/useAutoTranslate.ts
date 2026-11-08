import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGetAutoProgress, apiGetJobs } from '../services/api'

/** Poll backend auto-run + jobs so both skins share translating status. */
export function useWorkSync(workId: string | undefined) {
  const qc = useQueryClient()
  const { data: auto } = useQuery({
    queryKey: ['auto-progress', workId],
    queryFn: () => apiGetAutoProgress(workId!),
    enabled: !!workId,
    refetchInterval: (q) => (q.state.data?.running ? 2000 : 4000),
  })
  const { data: jobs } = useQuery({
    queryKey: ['jobs', workId],
    queryFn: () => apiGetJobs(workId!),
    enabled: !!workId,
    refetchInterval: 2000,
  })
  const prevRef = useRef('')
  useEffect(() => {
    if (!workId || !jobs) return
    const sig = jobs.map((j) => `${j.id}:${j.status}:${j.filename ?? ''}`).join('|')
    if (prevRef.current && prevRef.current !== sig) {
      qc.invalidateQueries({ queryKey: ['chapters', workId] })
      qc.invalidateQueries({ queryKey: ['works'] })
      qc.invalidateQueries({ queryKey: ['chapter', workId] })
      qc.invalidateQueries({ queryKey: ['auto-progress', workId] })
    }
    prevRef.current = sig
  }, [jobs, workId, qc])
  return { auto, jobs: jobs ?? [] }
}
