import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Colors } from '../../constants/Colors';
import { Spacing, ComponentSpacing } from '../../constants/Spacing';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { Display } from '../../components/Typography/Display';
import { Headline } from '../../components/Typography/Headline';
import { Body } from '../../components/Typography/Body';

/**
 * Results Page
 * 
 * Displays nutritional information and healthier alternatives.
 * Large, readable text with clear visual separation using surface containers.
 */
export default function Results() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    foodName?: string;
    healthAssessment?: string;
    nutritionalInfo?: string;
    alternatives?: string;
  }>();

  // Parse JSON data from params
  const nutritionalInfo = params.nutritionalInfo 
    ? JSON.parse(params.nutritionalInfo as string)
    : {};
  
  const alternatives = params.alternatives
    ? JSON.parse(params.alternatives as string)
    : [];

  const handleScanAnother = () => {
    router.navigate('/scanner');
  };

  return (
    <View style={styles.container}>
      <ScrollView 
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <Display size="small" color={Colors.primary}>
            {params.foodName || 'Your Food'}
          </Display>
        </View>

        {/* Health Assessment Card */}
        <Card elevated style={styles.assessmentCard}>
          <Headline size="small">Health Assessment</Headline>
          <Body size="large">
            {params.healthAssessment || 'Analyzing your food...'}
          </Body>
        </Card>

        {/* Nutritional Information Card */}
        <Card style={styles.nutritionCard}>
          <Headline size="small">Nutritional Information</Headline>
          {nutritionalInfo.calories !== undefined && (
            <View style={styles.nutrientItem}>
              <Body size="medium">🔥 Calories</Body>
              <Body size="small" color={Colors.on_surface_variant}>
                {nutritionalInfo.calories} kcal
              </Body>
            </View>
          )}
          {nutritionalInfo.carbohydrates !== undefined && (
            <View style={styles.nutrientItem}>
              <Body size="medium">🍚 Carbohydrates</Body>
              <Body size="small" color={Colors.on_surface_variant}>
                {nutritionalInfo.carbohydrates}g
              </Body>
            </View>
          )}
          {nutritionalInfo.protein !== undefined && (
            <View style={styles.nutrientItem}>
              <Body size="medium">🥩 Protein</Body>
              <Body size="small" color={Colors.on_surface_variant}>
                {nutritionalInfo.protein}g
              </Body>
            </View>
          )}
          {nutritionalInfo.fats !== undefined && (
            <View style={styles.nutrientItem}>
              <Body size="medium">🥑 Fats</Body>
              <Body size="small" color={Colors.on_surface_variant}>
                {nutritionalInfo.fats}g
              </Body>
            </View>
          )}
          {Object.keys(nutritionalInfo).length === 0 && (
            <Body size="medium" color={Colors.on_surface_variant}>
              Nutritional information will appear here when available
            </Body>
          )}
        </Card>

        {/* Healthier Alternatives Card */}
        <Card style={styles.alternativesCard}>
          <Headline size="small">Healthier Alternatives</Headline>
          {alternatives.length > 0 ? (
            alternatives.map((alt: any, index: number) => (
              <View key={index} style={styles.alternativeItem}>
                <Body size="medium">🌟 {alt.name}</Body>
                {alt.description && (
                  <Body size="small" color={Colors.on_surface_variant}>
                    {alt.description}
                  </Body>
                )}
              </View>
            ))
          ) : (
            <Body size="medium" color={Colors.on_surface_variant}>
              No alternatives suggested - this food might already be healthy! 🎉
            </Body>
          )}
        </Card>

        {/* Action Button */}
        <View style={styles.actionContainer}>
          <Button
            title="📷 Scan Another Food"
            onPress={handleScanAnother}
            style={styles.scanButton}
          />
        </View>

        {/* Tips Card */}
        <Card style={styles.tipsCard}>
          <Headline size="small">💡 Did You Know?</Headline>
          <Body size="medium">
            Eating a variety of colorful fruits and vegetables helps you get different vitamins and minerals!
          </Body>
        </Card>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.surface,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: ComponentSpacing.screen.horizontal,
    gap: Spacing.xl,
    paddingBottom: Spacing['4xl'],
  },
  header: {
    paddingTop: Spacing.md,
    paddingBottom: Spacing.sm,
  },
  assessmentCard: {
    backgroundColor: Colors.primary_container,
    gap: Spacing.md,
  },
  nutritionCard: {
    backgroundColor: Colors.surface_container_low,
    gap: Spacing.md,
  },
  nutrientItem: {
    gap: Spacing.xs,
    paddingVertical: Spacing.xs,
  },
  alternativesCard: {
    backgroundColor: Colors.secondary_container,
    gap: Spacing.md,
  },
  alternativeItem: {
    gap: Spacing.xs,
    paddingVertical: Spacing.xs,
  },
  placeholderText: {
    fontStyle: 'italic',
  },
  actionContainer: {
    marginTop: Spacing.md,
  },
  scanButton: {
    width: '100%',
  },
  tipsCard: {
    backgroundColor: Colors.surface_container_high,
    gap: Spacing.sm,
  },
});
