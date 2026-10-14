import * as am4core from '@amcharts/amcharts4/core';
import * as am4charts from '@amcharts/amcharts4/charts';
import am4themes_animated from '@amcharts/amcharts4/themes/animated';
import type { AnalysisPoint } from '../../types/api';

am4core.useTheme(am4themes_animated);

interface LineChartProps {
  data?: AnalysisPoint[];
}

const Line = (props: LineChartProps) => {
  const { data } = props;
  const CHART_ID = 'featureChart';
  const lightWhite = 'rgb(230, 230, 230)';

  let chart = am4core.create(CHART_ID, am4charts.XYChart);
  chart.data = data ?? [];

  chart.dateFormatter.dateFormat = 'yyyy';
  let dateAxis = chart.xAxes.push(new am4charts.DateAxis<am4charts.AxisRendererX>());
  dateAxis.gridIntervals.setAll([
    { timeUnit: 'year', count: 1 },
    { timeUnit: 'year', count: 5 },
    { timeUnit: 'year', count: 10 }
  ]);
  dateAxis.renderer.grid.template.stroke = am4core.color(lightWhite);
  dateAxis.renderer.labels.template.fontSize = 12;
  dateAxis.renderer.labels.template.fill = am4core.color(lightWhite);
  dateAxis.renderer.labels.template.opacity = 0.9;

  let valueAxis = chart.yAxes.push(new am4charts.ValueAxis<am4charts.AxisRendererY>());
  valueAxis.renderer.grid.template.stroke = am4core.color(lightWhite);
  valueAxis.renderer.labels.template.fontSize = 11;
  valueAxis.renderer.labels.template.fill = am4core.color(lightWhite);
  valueAxis.renderer.labels.template.opacity = 0.9;

  let seriesValue = chart.series.push(new am4charts.LineSeries());
  seriesValue.dataFields.dateX = 'year';
  seriesValue.dataFields.valueY = 'value';
  seriesValue.strokeWidth = 2;
  seriesValue.tensionX = 0.8;
  seriesValue.legendSettings.labelText = 'Annual Average';
  seriesValue.stroke = am4core.color('rgb(68, 54, 119)');
  seriesValue.strokeDasharray = '3,3';

  let seriesRolling = chart.series.push(new am4charts.LineSeries());
  seriesRolling.dataFields.dateX = 'year';
  seriesRolling.dataFields.valueY = 'rolling';
  seriesRolling.strokeWidth = 2;
  seriesRolling.tensionX = 0.8;
  seriesRolling.legendSettings.labelText = '3 Year Rolling Average';
  seriesRolling.stroke = am4core.color('rgb(128,103,220)');

  chart.cursor = new am4charts.XYCursor();
  chart.cursor.xAxis = dateAxis;
  chart.cursor.lineX.stroke = am4core.color(lightWhite);
  chart.cursor.lineX.strokeWidth = 2;
  chart.cursor.lineX.strokeDasharray = '2,2';
  chart.cursor.lineY.stroke = am4core.color(lightWhite);
  chart.cursor.lineY.strokeWidth = 2;
  chart.cursor.lineY.strokeDasharray = '2,2';
  chart.cursor.snapToSeries = [seriesValue, seriesRolling];

  chart.legend = new am4charts.Legend();
  chart.legend.position = 'bottom';
  chart.legend.contentAlign = 'right';
  chart.legend.labels.template.fontSize = 14;
  chart.legend.labels.template.fontWeight = '300';
  chart.legend.labels.template.fill = am4core.color(lightWhite);
  chart.legend.labels.template.opacity = 0.9;
  chart.legend.itemContainers.template.paddingTop = 0;
  chart.legend.itemContainers.template.paddingBottom = 0;

  // chart.dispose();

  return (
    <div
      id={CHART_ID}
      style={{
        width: '100%',
        height: '260px',
        marginTop: '10px',
        marginRight: '20px'
      }}
    />
  );
};

export default Line;
