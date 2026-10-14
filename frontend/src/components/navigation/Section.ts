import styled from 'styled-components';

const Section = styled.div<{ activeTab: boolean }>`
  ${(props) => (props.activeTab ? '' : 'display:none')}
`;

export default Section;
