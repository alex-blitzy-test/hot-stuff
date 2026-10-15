import * as am4core from '@amcharts/amcharts4/core';
import * as am4charts from '@amcharts/amcharts4/charts';
import am4themes_animated from '@amcharts/amcharts4/themes/animated';

import type { FeatureAverage } from '../../types/api';

am4core.useTheme(am4themes_animated);

type RadarProps = {
  data?: FeatureAverage[];
};

const Radar = (props: RadarProps) => {
  const { data } = props;
  const CHART_ID = 'radialChart';
  const lightWhite = 'rgb(230, 230, 230)';

  var chart = am4core.create(CHART_ID, am4charts.RadarChart);
  // amCharts declares `Component.data` as a non-optional array, so an absent payload is normalized to an empty set,
  // which renders exactly like the `undefined` the parent passes before a week has loaded.
  chart.data = data ?? [];

  // Make chart not full circle
  chart.startAngle = -90;
  chart.endAngle = 180;
  chart.innerRadius = am4core.percent(30);

  // Set number format
  chart.numberFormatter.numberFormat = '###';

  // Create axes
  var categoryAxis = chart.yAxes.push(
    new am4charts.CategoryAxis<am4charts.AxisRendererRadial>()
  );
  categoryAxis.dataFields.category = 'feature';
  categoryAxis.renderer.grid.template.strokeOpacity = 0;
  categoryAxis.renderer.labels.template.horizontalCenter = 'right';
  categoryAxis.renderer.labels.template.fontSize = 16;
  categoryAxis.renderer.labels.template.adapter.add(
    'fill',
    function (fill, target) {
      return target.dataItem.index >= 0
        ? chart.colors.getIndex(target.dataItem.index)
        : fill;
    }
  );
  categoryAxis.renderer.minGridDistance = 10;

  var valueAxis = chart.xAxes.push(
    new am4charts.ValueAxis<am4charts.AxisRendererCircular>()
  );
  valueAxis.renderer.grid.template.strokeOpacity = 0;
  valueAxis.min = 0;
  valueAxis.max = 100;
  valueAxis.strictMinMax = true;
  valueAxis.renderer.labels.template.fontSize = 11;
  valueAxis.renderer.labels.template.fill = am4core.color(lightWhite);
  valueAxis.renderer.labels.template.fillOpacity = 0.8;

  var series1 = chart.series.push(new am4charts.RadarColumnSeries());
  series1.dataFields.valueX = 'full';
  series1.dataFields.categoryY = 'feature';
  series1.clustered = false;
  series1.columns.template.fill = am4core.color('#262626');
  series1.columns.template.strokeWidth = 0;
  series1.columns.template.radarColumn.cornerRadius = 5;

  var series2 = chart.series.push(new am4charts.RadarColumnSeries());
  series2.dataFields.valueX = 'mean';
  series2.dataFields.categoryY = 'feature';
  series2.columns.template.strokeWidth = 0;
  series2.columns.template.tooltipText = '{mean}';
  series2.columns.template.radarColumn.cornerRadius = 5;
  series2.columns.template.adapter.add('fill', function (fill, target) {
    return target.dataItem
      ? chart.colors.getIndex(target.dataItem.index)
      : fill;
  });

  // chart.dispose();

  return (
    <div
      id={CHART_ID}
      style={{
        width: '100%',
        height: '260px'
      }}
    />
  );
};

export default Radar;
