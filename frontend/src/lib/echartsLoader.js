let echartsPromise = null

export const loadEcharts = async () => {
  if (!echartsPromise) {
    echartsPromise = import('./echartsCore').then((module) => module.echarts)
  }
  return echartsPromise
}
