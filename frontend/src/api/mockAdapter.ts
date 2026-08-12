export const mockAdapter = {
  getHealth: async () => {
    await new Promise((resolve) => setTimeout(resolve, 200));
    return { status: 'ok', source: 'mock' };
  },
};

