import React from 'react';
import clsx from 'clsx';
import {ThemeClassNames} from '@docusaurus/theme-common';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import Heading from '@theme/Heading';
import MDXContent from '@theme/MDXContent';
import AudienceBadge from '@site/src/components/AudienceBadge';
import FeatureStatus from '@site/src/components/FeatureStatus';
import SiteBackLink from '@site/src/components/SiteBackLink';
import type {Audience} from '@site/src/components/AudienceBadge';
import type {FeatureStatusValue} from '@site/src/components/FeatureStatus';

function useSyntheticTitle() {
  const {metadata, frontMatter, contentTitle} = useDoc();
  const shouldRender = !frontMatter.hide_title && typeof contentTitle === 'undefined';
  if (!shouldRender) return null;
  return metadata.title;
}

export default function DocItemContent({children}: {children: React.ReactNode}) {
  const syntheticTitle = useSyntheticTitle();
  const {frontMatter} = useDoc();
  const audience = (frontMatter as {audience?: Audience}).audience;
  const status = (frontMatter as {status?: FeatureStatusValue}).status;

  return (
    <div className={clsx(ThemeClassNames.docs.docMarkdown, 'markdown')}>
      <SiteBackLink />
      {audience && (
        <div className="audience-badge-row"><AudienceBadge audience={audience} /></div>
      )}
      {syntheticTitle && (
        <header>
          <Heading as="h1">{syntheticTitle}</Heading>
        </header>
      )}
      {status && <FeatureStatus status={status} />}
      <MDXContent>{children}</MDXContent>
    </div>
  );
}
