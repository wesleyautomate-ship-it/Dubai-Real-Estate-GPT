import { create } from 'zustand';

const initialState = {
  conversations: [],
  status: 'idle',
  error: null,
  page: 1,
  pageSize: 10,
  total: null,
  hasMore: false,
  lastFetchedAt: null,
};

const useConversationStore = create((set, get) => ({
  ...initialState,

  setPageSize: (size) => {
    if (!Number.isFinite(size) || size <= 0) return;
    set({ pageSize: Math.floor(size) });
  },

  startLoading: (page = 1) =>
    set((state) => ({
      status: 'loading',
      error: null,
      page,
      conversations: page === 1 ? [] : state.conversations,
    })),

  setSuccess: ({ items, page, pageSize, total }) =>
    set((state) => {
      const normalizedPage = page ?? state.page ?? 1;
      const effectivePageSize = pageSize ?? state.pageSize;
      const nextTotal = typeof total === 'number' ? total : state.total;

      const existing = normalizedPage === 1 ? [] : state.conversations;
      const existingIds = new Set(existing.map((item) => item?.id));
      const deduped = (items || []).filter((item) => {
        const key = item?.id;
        if (key == null || existingIds.has(key)) {
          return normalizedPage === 1; // allow replacing when refreshing first page even if ids missing
        }
        existingIds.add(key);
        return true;
      });

      const merged = normalizedPage === 1 ? deduped : [...existing, ...deduped];
      const receivedNewCount = normalizedPage === 1 ? deduped.length : deduped.length;
      const computedHasMore = (() => {
        if (normalizedPage === 1 && deduped.length === 0) {
          return false;
        }
        if (typeof nextTotal === 'number') {
          return merged.length < nextTotal;
        }
        if (deduped.length === 0) {
          return false;
        }
        return deduped.length >= effectivePageSize;
      })();

      return {
        conversations: merged,
        status: 'success',
        error: null,
        page: normalizedPage,
        pageSize: effectivePageSize,
        total: nextTotal,
        hasMore: computedHasMore,
        lastFetchedAt: Date.now(),
      };
    }),

  setFailure: (error) =>
    set((state) => ({
      status: 'error',
      error,
      page: state.page,
    })),

  reset: () => set({ ...initialState }),
}));

export default useConversationStore;
