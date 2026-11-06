import { useQuery } from '@tanstack/react-query'
import { apiGetWorks } from '../services/api'

/** Look up a work's display name by its work_id. Falls back to the id
 * itself if the works list hasn't loaded yet. */
export function useWorkName(workId: string | undefined): string {
  const { data: works } = useQuery({
    queryKey: ['works'],
    queryFn: apiGetWorks,
  })
  if (!workId) return ''
  return works?.find((w) => w.id === workId)?.name ?? workId
}
