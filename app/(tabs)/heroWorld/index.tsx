import AppHeader from "@/components/app_header";
import { Colors } from "@/constants/colors";
import { Typography } from "@/constants/fonts";
import { Radius } from "@/constants/radius";
import { Spacing } from "@/constants/spacing";
import { ChevronRight, Gamepad2 } from "lucide-react-native";
import { Image, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import React from "react";
import { AutoSizeText, ResizeTextMode } from "react-native-auto-size-text";


const GAME_ID = 'xx';
const CARD_GAP = Spacing.md;

interface GameTile {
  id: string;
  title: string;
  emoji: string;
  description: string;
  route: string;
  available: boolean;
}

const GAMES: GameTile[] = [
  {
    id: GAME_ID,
    title: 'Meal Maker',
    emoji: '🍽️',
    description: 'Build healthy meals!',
    route: '/(tabs)/heroWorld/meal-maker',
    available: true,
  },
  {
    id: 'coming-soon-1',
    title: 'Coming Soon',
    emoji: '🔒',
    description: 'More games on the way!',
    route: '',
    available: false,
  },
];

export default function HeroWorldScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const handleGamePress = (game: GameTile) => {
    if (game.available && game.route) {
      router.push(game.route as any);
    }
  };

  const renderGameTile = ({ item }: { item: GameTile }) => {
    // const highScore = highScores[item.id] ?? 0;
    const highScore = 0;

    return (
      <TouchableOpacity
        style={[styles.gameCard, !item.available && styles.cardDisabled]}
        onPress={() => handleGamePress(item)}
        activeOpacity={item.available ? 0.8 : 1}
        disabled={!item.available}
      >
        <Text style={styles.cardEmoji}>{item.emoji}</Text>
        <Text style={[styles.cardTitle, !item.available && styles.cardTitleDisabled]}>
          {item.title}
        </Text>
        <AutoSizeText fontSize={16} mode={ResizeTextMode.max_lines} style={styles.cardDescription} numberOfLines={2}>
          {item.description}
        </AutoSizeText>
        {item.available && highScore > 0 && (
          <View style={styles.highScoreBadge}>
            <Text style={styles.highScoreText}>⭐ Best: {highScore}</Text>
          </View>
        )}
      </TouchableOpacity>
    );
  };

  return (
    <View style={[styles.safeArea, { paddingTop: insets.top }]}>
      <ScrollView contentContainerStyle={styles.container}>
        <AppHeader/>

        <Image
          source={require('../../../assets/images/nutriheroes_logo_tight.png')}
          style={styles.bannerImage}
          resizeMode='contain'
        />
        <View style={styles.bannerTextContainer}>
          <Text style={styles.bannerText}>🌎 Hero World</Text>
        </View>

        {/* Daily Challenge */}
        <TouchableOpacity 
          style={styles.card}
          onPress={() => router.push('/(tabs)/heroWorld/daily-challenge' as any)}
        >
          <Text style={{
            fontSize: 32,
            padding: Spacing.md,
            margin: Spacing.md,
            backgroundColor: Colors.primary_container,
            borderRadius: 999
          }}>🥦</Text>
          <View style={styles.cardTextContainer}>
            <Text style={styles.cardHeader}>DAILY CHALLENGE</Text>
            <Text style={styles.cardTitle}>Eat something green today!</Text>
            <Text style={styles.cardSubtext}>Small bite, big power!</Text>
          </View>
          <View style={styles.buttonContainer}>
            <View style={styles.button}>
              <ChevronRight color={Colors.on_secondary}></ChevronRight>
            </View>
          </View>
        </TouchableOpacity>

        {/* Games section */}
        <View>
          <View style={styles.sectionHeader}>
            <Gamepad2 color={styles.sectionHeaderText.color} size={Spacing["2xl"]} style={{margin: Spacing.xs}}></Gamepad2>
            <Text style={styles.sectionHeaderText}>Fun & Games</Text>
          </View>
          <View style={styles.grid}>
            <View style={styles.row}>
              {GAMES.map((game) => (
                <View style={{width: '50%', height: 'auto'}} key={game.id}>
                  {renderGameTile({ item: game })}
                </View>
              ))}
            </View>
          </View>
        </View>
      </ScrollView>
    </View>
  )
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.surface,
  },
  container: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.sm,
    flexGrow: 1,
  },
  bannerImage: {
    alignSelf: 'center',
    width: '80%',
    height: '30%',
  },
  bannerTextContainer: {
    position: 'relative',
    top: -Spacing.lg,
    backgroundColor: Colors.on_primary,
    borderRadius: Radius.badge,
    borderWidth: Spacing.spacing_1,
    borderColor: '#E8D7C7',
    paddingHorizontal: Spacing["2xl"],
    paddingVertical: Spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center'
  },
  bannerText: {
    color: Colors.secondary_dim,
    ...Typography.headlineLarge
  },
  card: {
    backgroundColor: Colors.on_primary,
    borderRadius: Spacing.xl,
    flexDirection: 'row',
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
  cardTextContainer: {
    alignItems: 'flex-start',
    padding: Spacing.xs,
    paddingLeft: 0
  },
  cardHeader: {
    ...Typography.bodyLarge,
    color: Colors.primary,
  },
  cardTitle: {
    ...Typography.bodySmall
  },
  cardSubtext: {
    ...Typography.bodySmall,
    color: Colors.on_surface_variant
  },
  buttonContainer: {
    justifyContent: 'center',
    marginLeft: 'auto',
    marginRight: Spacing.md
  },
  button: {
    backgroundColor: Colors.secondary_dim,
    borderRadius: Radius.badge,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    margin: Spacing.md
  },
  sectionHeaderText: {
    ...Typography.headlineLarge,
    color: Colors.on_surface_variant
  },
  grid: {
    paddingHorizontal: Spacing.xl,
    paddingBottom: Spacing.xl,
  },
  row: {
    gap: CARD_GAP,
    marginBottom: CARD_GAP,
    flexDirection: 'row'
  },
  gameCard: {
    backgroundColor: Colors.surface_container_lowest,
    borderRadius: Radius.card,
    padding: Spacing.lg,
    alignItems: 'center',
    gap: Spacing.xs,
    shadowColor: Colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 3,
  },
  cardDisabled: {
    backgroundColor: Colors.surface_container_high,
    opacity: 0.6,
  },
  cardEmoji: {
    fontSize: 48,
    marginBottom: Spacing.xs,
  },
  cardTitleDisabled: {
    color: Colors.on_surface_variant,
  },
  cardDescription: {
    ...Typography.bodySmall,
    color: Colors.on_surface_variant,
    textAlign: 'center',
  },
  highScoreBadge: {
    marginTop: Spacing.xs,
    backgroundColor: Colors.primary_container,
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
  },
  highScoreText: {
    ...Typography.labelSmall,
    color: Colors.on_primary_container,
  },
  comingSoonBadge: {
    marginTop: Spacing.xs,
    backgroundColor: Colors.surface_container_highest,
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
  },
  comingSoonText: {
    ...Typography.labelSmall,
    color: Colors.on_surface_variant,
  },
});
