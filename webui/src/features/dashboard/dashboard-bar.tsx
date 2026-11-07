import { Bar } from "@ant-design/charts"

// R-14：dashboard 专属的图表门面模块。dashboard-workspace 用 React.lazy
// 动态 import 本文件，让 @ant-design/charts（charts-vendor 约 1.3MB）只在
// 打开运维控制台时加载，不进入首屏。
export default Bar
