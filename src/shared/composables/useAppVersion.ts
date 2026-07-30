export const useAppVersion = () => {
  const version = __APP_VERSION__
  const buildDate = `${new Date(__BUILD_DATE__).toLocaleDateString()} ${new Date(__BUILD_DATE__).toLocaleTimeString()}`

  return {
    version,
    buildDate,
  }
}
